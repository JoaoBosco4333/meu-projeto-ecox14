from datetime import datetime
import json
from pathlib import Path
import pandas as pd

import limpeza  

BRONZE = Path("dados/bronze")
PRATA = Path("dados/prata")
PADRAO = "SIM_*.csv"

# Níveis de escolaridade válidos do DataSUS (0: Nenhuma, 1: 1-3 anos, ..., 5: Superior completo)
# O código 9 (Ignorado) é deixado de fora para ser tratado como valor nulo/ausente
ORDEM_ESCOLARIDADE = [0, 1, 2, 3, 4, 5]


def carregar():
    """Busca o arquivo mais recente do SIM na camada Bronze e realiza a leitura inicial."""
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")

    # Seleciona o arquivo mais recente da lista ordenada
    caminho = arquivos[-1]
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", low_memory=False)
    print("lido:", caminho.name, df.shape)
    return df, caminho


def conferir_chave(df, chave="contador"):
    """Verifica e remove registros totalmente duplicados com base na coluna chave primária."""
    repetidas = df[chave].duplicated().sum()
    print("linhas identicas (chave repetida):", repetidas)
    if repetidas:
        print(df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


def remover_colunas_mortas(df, colunas=("CB_PRE",)):
    """Elimina colunas que não agregam valor analítico (ex: 100% nulas ou depreciadas)."""
    presentes = [c for c in colunas if c in df.columns]
    print("colunas removidas (100% vazias / tipo nao suportado):", presentes)
    return df.drop(columns=presentes)


def resolver_escolaridade(df):
    """Remove o padrão antigo de escolaridade ('ESC'), mantendo apenas o padrão mais recente ('ESC2010')."""
    if "ESC" in df.columns:
        print("ESC removida; mantida ESC2010 (padrao mais recente)")
        df = df.drop(columns=["ESC"])
    return df


def tipar_escolaridade(df):
    """Converte 'ESC2010' para inteiro com suporte a Nulos (Int64) e aplica ordenação categórica."""
    df["ESC2010"] = pd.to_numeric(df["ESC2010"], errors="coerce").astype(
        "Int64"
    )
    return limpeza.tipar_categoria_ordenada(df, "ESC2010", ORDEM_ESCOLARIDADE)


def decodificar_idade(df):
    """Decodifica o campo IDADE no formato nativo do DataSUS (Unidade + Quantidade).

    Estrutura do código:
    - 000: Idade ignorada -> pd.NA
    - 1xx, 2xx, 3xx: Minutos, Horas, Dias (menores de 1 ano) -> 0 anos
    - 4xx: Anos de vida (ex: 445 = 45 anos) -> 45
    - 5xx: Maior de 100 anos (ex: 505 = 105 anos) -> 105
    """

    def decodifica(codigo):
        if pd.isna(codigo):
            return pd.NA
        codigo = int(codigo)
        if codigo == 0:
            return pd.NA  # Código para idade ignorada

        unidade, quantidade = codigo // 100, codigo % 100

        if unidade in (0, 1, 2, 3):
            return 0  # Menor de 1 ano de idade
        if unidade == 4:
            return quantidade
        if unidade == 5:
            return 100 + quantidade
        return pd.NA

    df["idade_anos"] = df["IDADE"].apply(decodifica)
    return df


def converter_datas(df, colunas=("DTOBITO", "DTNASC")):
    """Padroniza colunas numéricas de data no formato DDMMAAAA para o tipo datetime do Pandas."""
    for col in colunas:
        if col in df.columns:
            bruto = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            # zfill(8) garante que datas com zero à esquerda (ex: 1012020) virem "01012020"
            df[col] = pd.to_datetime(
                bruto.astype(str).str.zfill(8),
                format="%d%m%Y",
                errors="coerce",
            )
    return df


def limites_iqr(serie):
    """Calcula os limites inferior e superior para detecção de outliers pelo método IQR (Amplitude Interquartil)."""
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_extremos(df, coluna):
    """Adiciona uma flag booleana indicando se o valor é um outlier com base no IQR."""
    valida = df[coluna].dropna()
    baixo, alto = limites_iqr(valida)
    df[coluna + "_extremo"] = (df[coluna] < baixo) | (df[coluna] > alto)
    print(coluna, "extremos (IQR):", df[coluna + "_extremo"].sum())
    return df


def marcar_zscore(df, coluna, limite=3):
    """Adiciona uma flag booleana indicando se o valor afasta-se mais de `limite` desvios-padrão da média (Z-Score)."""
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_z"] = z.abs() > limite
    print(coluna, "extremos (z-score):", df[coluna + "_z"].sum())
    return df


def remover_erros_idade(df, minimo=0, maximo=130):
    """Filtra e remove registros com idades biologicamente impossíveis (mantendo os valores ausentes)."""
    valido = df["idade_anos"].between(minimo, maximo) | df["idade_anos"].isna()
    print("removidas (idade fora de 0-130 anos):", (~valido).sum())
    return df[valido].copy()


def salvar(df):
    """Exporta o DataFrame limpo da camada Prata no formato binário de alta performance Apache Parquet."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "sim.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    """Registra a proveniência e a linhagem dos dados em um log JSON Lines (JSONL)."""
    info = {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    """Pipeline principal de higienização, transformação e gravação da camada Prata do SIM."""
    df, origem = carregar()
    antes = len(df)

    # Execução encadeada de etapas de limpeza
    df = limpeza.tirar_espacos(df)
    df = conferir_chave(df)
    df = remover_colunas_mortas(df)
    df = resolver_escolaridade(df)
    df = tipar_escolaridade(df)
    df = decodificar_idade(df)
    df = converter_datas(df)
    df = marcar_extremos(df, "idade_anos")
    df = marcar_zscore(df, "idade_anos")
    df = remover_erros_idade(df)

    # Persistência e auditoria de proveniência
    destino = salvar(df)
    registrar(
        origem,
        destino,
        antes,
        len(df),
        [
            "linhas identicas verificadas por contador",
            "CB_PRE removida (100% vazia)",
            "ESC removida, mantida ESC2010",
            (
                "ESC2010 tipada como categoria ordenada (0-5); 9=ignorado vira"
                " ausente"
            ),
            (
                "IDADE decodificada em idade_anos (padrao DATASUS"
                " unidade+quantidade)"
            ),
            "DTOBITO e DTNASC convertidas para data",
            "idade_anos fora de 0-130 removida (erro comprovado)",
            "idade_anos marcada com extremos via IQR e z-score",
        ],
    )


if __name__ == "__main__":
    main()