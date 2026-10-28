from datetime import datetime
import json
from pathlib import Path
import pandas as pd

import limpeza 


BRONZE = Path("dados/bronze")
PRATA = Path("dados/prata")
PADRAO = "SINASC_*.csv"

# Escolaridade da mãe: 0-5 são válidos; 9 (ignorado) fica fora de propósito
ORDEM_ESCOLARIDADE = [0, 1, 2, 3, 4, 5]

# Limites clínicos para faixas de peso ao nascer (em gramas)
CORTES_PESO = [0, 2500, 4000, float("inf")]
ROTULOS_PESO = ["baixo peso", "peso normal", "alto peso"]


def criar_faixa_peso(df):
    """Categoriza a coluna 'PESO' nas faixas médicas recomendadas da OMS."""
    return limpeza.faixa_por_corte(df, "PESO", CORTES_PESO, ROTULOS_PESO)


def carregar():
    """Carrega o arquivo mais recente do SINASC contido na camada Bronze."""
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", low_memory=False)
    print("lido:", caminho.name, df.shape)
    return df, caminho


def conferir_chave(df, chave="contador"):
    """Garante a unicidade dos dados removendo linhas duplicadas com base no identificador."""
    repetidas = df[chave].duplicated().sum()
    print("linhas identicas (chave repetida):", repetidas)
    if repetidas:
        print(df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


def converter_datas(df, colunas=("DTNASC", "DTULTMENST", "DTDECLARAC")):
    """Converte colunas de datas da DNV (Declaração de Nascido Vivo) para datetime."""
    for col in colunas:
        if col in df.columns:
            bruto = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            df[col] = pd.to_datetime(
                bruto.astype(str).str.zfill(8),
                format="%d%m%Y",
                errors="coerce",
            )
    return df


def converter_tipos(df):
    """Converte colunas numéricas de contagem/medida do SINASC para o tipo numérico apropriado."""
    numericas = [
        "PESO",
        "APGAR1",
        "APGAR5",
        "IDADEMAE",
        "QTDFILVIVO",
        "QTDFILMORT",
        "SEMAGESTAC",
    ]
    for col in numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def tipar_escolaridade(df):
    """Tipa e ordena a coluna da escolaridade da mãe (ESCMAE2010)."""
    df["ESCMAE2010"] = pd.to_numeric(
        df["ESCMAE2010"], errors="coerce"
    ).astype("Int64")
    return limpeza.tipar_categoria_ordenada(
        df, "ESCMAE2010", ORDEM_ESCOLARIDADE
    )


def remover_erros_apgar(df):
    """Remove registros com pontuações de APGAR inconsistentes (fora do intervalo válido da escala 0-10)."""
    for col in ("APGAR1", "APGAR5"):
        valido = df[col].between(0, 10) | df[col].isna()
        print(f"{col} fora de 0-10 (erro comprovado):", (~valido).sum())
        df = df[valido].copy()
    return df


def remover_erros_peso(df, minimo=200, maximo=7000):
    """Filtra e descarta registros com pesos (em gramas) fora dos limites biológicos aceitáveis."""
    valido = df["PESO"].between(minimo, maximo) | df["PESO"].isna()
    print(
        f"PESO fora de {minimo}-{maximo}g (erro comprovado):", (~valido).sum()
    )
    return df[valido].copy()


def limites_iqr(serie):
    """Cálculo da amplitude interquartil (IQR) para detecção de anomalias."""
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_extremos(df, coluna):
    """Gera flag de indicação para valores extremos via limite IQR em colunas numéricas."""
    valida = df[coluna].dropna()
    baixo, alto = limites_iqr(valida)
    df[coluna + "_extremo"] = (df[coluna] < baixo) | (df[coluna] > alto)
    print(coluna, "extremos (IQR):", df[coluna + "_extremo"].sum())
    return df


def marcar_zscore(df, coluna, limite=3):
    """Gera flag de indicação para valores de peso extremos utilizando Z-Score."""
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_z"] = z.abs() > limite
    print(coluna, "extremos (z-score):", df[coluna + "_z"].sum())
    return df


def salvar(df):
    """Grava o dataset processado do SINASC em formato Parquet dentro da pasta Prata."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "sinasc.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destination if (destination := destino) else destino


def registrar(origem, destino, antes, depois, decisoes):
    """Salva os logs da transformação da camada Prata garantindo rastreabilidade no arquivo JSONL."""
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
    """Pipeline principal de higienização do SINASC para formação da Camada Prata."""
    df, origem = carregar()
    antes = len(df)

    # Execução encadeada do pipeline de limpeza do SINASC
    df = limpeza.tirar_espacos(df)
    df = conferir_chave(df)
    df = converter_datas(df)
    df = converter_tipos(df)
    df = tipar_escolaridade(df)
    df = remover_erros_apgar(df)
    df = remover_erros_peso(df)
    df = marcar_extremos(df, "PESO")
    df = marcar_zscore(df, "PESO")
    df = criar_faixa_peso(df)

    # Exportação e escrita de metadados de linhagem
    destino = salvar(df)
    registrar(
        origem,
        destino,
        antes,
        len(df),
        [
            "linhas identicas verificadas por contador",
            "DTNASC, DTULTMENST, DTDECLARAC convertidas para data",
            (
                "PESO, APGAR1, APGAR5, IDADEMAE, QTDFILVIVO, QTDFILMORT,"
                " SEMAGESTAC convertidas para numero"
            ),
            (
                "ESCMAE2010 tipada como categoria ordenada (0-5); 9=ignorado vira"
                " ausente"
            ),
            (
                "APGAR1/APGAR5 fora de 0-10 removidos (erro comprovado, faixa"
                " fixa da escala)"
            ),
            (
                "PESO fora de 200-7000g removido (erro comprovado, limite"
                " biologico)"
            ),
            "PESO marcado com extremos via IQR e z-score",
        ],
    )


if __name__ == "__main__":
    main()