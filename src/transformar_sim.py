import json
from datetime import datetime
from pathlib import Path
import pandas as pd

BRONZE = Path("dados/bronze")
PRATA = Path("dados/prata")
PADRAO = "SIM_*.csv"


def carregar():
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", low_memory=False)
    print("lido:", caminho.name, df.shape)
    return df, caminho


def tirar_espacos(df):
    df.columns = df.columns.str.strip()
    for coluna in df.select_dtypes(include="object"):
        df[coluna] = df[coluna].str.strip()
    return df


def conferir_chave(df, chave="contador"):
    repetidas = df[chave].duplicated().sum()
    print("linhas identicas (chave repetida):", repetidas)
    if repetidas:
        print(df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


def remover_colunas_mortas(df, colunas=("CB_PRE",)):
    presentes = [c for c in colunas if c in df.columns]
    print("colunas removidas (100% vazias / tipo nao suportado):", presentes)
    return df.drop(columns=presentes)


def resolver_escolaridade(df):
    if "ESC" in df.columns:
        print("ESC removida; mantida ESC2010 (padrao mais recente)")
        df = df.drop(columns=["ESC"])
    return df


def decodificar_idade(df):
    def decodifica(codigo):
        if pd.isna(codigo):
            return pd.NA
        codigo = int(codigo)
        if codigo == 0:
            return pd.NA  # idade ignorada
        unidade, quantidade = codigo // 100, codigo % 100
        if unidade in (0, 1, 2, 3):
            return 0  # menor de 1 ano
        if unidade == 4:
            return quantidade
        if unidade == 5:
            return 100 + quantidade
        return pd.NA

    df["idade_anos"] = df["IDADE"].apply(decodifica)
    return df


def converter_datas(df, colunas=("DTOBITO", "DTNASC")):
    for col in colunas:
        if col in df.columns:
            bruto = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            df[col] = pd.to_datetime(
                bruto.astype(str).str.zfill(8), format="%d%m%Y", errors="coerce"
            )
    return df


def limites_iqr(serie):
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_extremos(df, coluna):
    valida = df[coluna].dropna()
    baixo, alto = limites_iqr(valida)
    df[coluna + "_extremo"] = (df[coluna] < baixo) | (df[coluna] > alto)
    print(coluna, "extremos (IQR):", df[coluna + "_extremo"].sum())
    return df


def marcar_zscore(df, coluna, limite=3):
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_z"] = z.abs() > limite
    print(coluna, "extremos (z-score):", df[coluna + "_z"].sum())
    return df


def remover_erros_idade(df, minimo=0, maximo=130):
    valido = df["idade_anos"].between(minimo, maximo) | df["idade_anos"].isna()
    print("removidas (idade fora de 0-130 anos):", (~valido).sum())
    return df[valido].copy()


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "sim.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
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
    df, origem = carregar()
    antes = len(df)
    df = tirar_espacos(df)
    df = conferir_chave(df)
    df = remover_colunas_mortas(df)
    df = resolver_escolaridade(df)
    df = decodificar_idade(df)
    df = converter_datas(df)
    df = marcar_extremos(df, "idade_anos")
    df = marcar_zscore(df, "idade_anos")
    df = remover_erros_idade(df)
    destino = salvar(df)
    registrar(origem, destino, antes, len(df), [
        "linhas identicas verificadas por contador",
        "CB_PRE removida (100% vazia)",
        "ESC removida, mantida ESC2010",
        "IDADE decodificada em idade_anos (padrao DATASUS unidade+quantidade)",
        "DTOBITO e DTNASC convertidas para data",
        "idade_anos fora de 0-130 removida (erro comprovado)",
        "idade_anos marcada com extremos via IQR e z-score",
    ])


if __name__ == "__main__":
    main()