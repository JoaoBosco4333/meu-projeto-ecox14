"""Transformacao (Prata) da terceira fonte: populacao por municipio, IBGE."""
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

import limpeza

BRONZE = Path("dados/bronze/ibge/populacao_municipios")
PRATA = Path("dados/prata")
PADRAO = "populacao_*.csv"


def carregar():
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    print("lido:", caminho.name, df.shape)
    return df, caminho


def converter_tipos(df):
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce").astype("Int64")
    return df


def criar_chave_municipio(df):
    """IBGE usa codigo de 7 digitos (com digito verificador).
    DATASUS usa codigo de 6 digitos (sem o verificador).
    Cria a chave compativel removendo o ultimo digito."""
    df["codigo_municipio_6"] = (df["codigo_municipio"] // 10).astype("Int64")
    return df


def criar_regiao(df):
    """Primeiro digito do codigo do municipio define a macrorregiao."""
    mapa_regiao = {
        "1": "Norte", "2": "Nordeste", "3": "Sudeste",
        "4": "Sul", "5": "Centro-Oeste",
    }
    primeiro_digito = df["codigo_municipio"].astype(str).str[0]
    df["regiao"] = primeiro_digito.map(mapa_regiao)
    print("municipios sem regiao mapeada:", df["regiao"].isna().sum())
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "populacao.parquet"
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
    df = limpeza.tirar_espacos(df)
    df = converter_tipos(df)
    df = criar_chave_municipio(df)
    df = criar_regiao(df)
    destino = salvar(df)
    registrar(origem, destino, antes, len(df), [
        "ano e populacao convertidos para Int64",
        "codigo_municipio_6 criado (remove digito verificador, compativel com DATASUS)",
        "regiao derivada do primeiro digito do codigo do municipio",
    ])


if __name__ == "__main__":
    main()