"""Camada Ouro: junta SIM + SINASC + populacao (IBGE) por municipio
e calcula taxa de mortalidade infantil e taxa de natalidade por regiao."""
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

PRATA = Path("dados/prata")
OURO = Path("dados/ouro")


def carregar():
    sim = pd.read_parquet(PRATA / "sim.parquet")
    sinasc = pd.read_parquet(PRATA / "sinasc.parquet")
    populacao = pd.read_parquet(PRATA / "populacao.parquet")
    print("sim:", sim.shape, "| sinasc:", sinasc.shape, "| populacao:", populacao.shape)
    return sim, sinasc, populacao


def obitos_infantis_por_municipio(sim):
    """Obitos com idade_anos == 0 (menor de 1 ano), por municipio."""
    infantil = sim[sim["idade_anos"] == 0]
    contagem = infantil.groupby("CODMUNRES").size().rename("obitos_infantis")
    print("obitos infantis (Brasil):", contagem.sum(), "de", len(sim), "obitos totais no SIM")
    return contagem.reset_index()


def nascimentos_por_municipio(sinasc):
    contagem = sinasc.groupby("CODMUNRES").size().rename("nascimentos")
    print("nascimentos (Brasil):", contagem.sum())
    return contagem.reset_index()


def preparar_chaves(obitos, nascimentos, populacao):
    """Garante o mesmo tipo/nome de codigo de municipio nas tres tabelas."""
    obitos["CODMUNRES"] = pd.to_numeric(obitos["CODMUNRES"], errors="coerce").astype("Int64")
    nascimentos["CODMUNRES"] = pd.to_numeric(nascimentos["CODMUNRES"], errors="coerce").astype("Int64")
    populacao = populacao.rename(columns={"codigo_municipio_6": "CODMUNRES"})
    return obitos, nascimentos, populacao


def checar_nao_casados(nome, tabela, populacao):
    """Confere codigos de municipio que nao existem na base de populacao
    (ex: codigo de 'ignorado' ou residente no exterior) - essas linhas
    ficam de fora da conta por regiao, e isso precisa ficar visivel."""
    validos = set(populacao["CODMUNRES"].dropna().unique())
    fora = set(tabela["CODMUNRES"].dropna().unique()) - validos
    linhas_fora = tabela[tabela["CODMUNRES"].isin(fora)]
    print(f"{nome}: {len(fora)} codigo(s) de municipio fora da base do IBGE "
          f"({linhas_fora.shape[0]} registros afetados, ex: {list(fora)[:5]})")
    return fora


def juntar_por_municipio(obitos, nascimentos, populacao):
    base = populacao[["CODMUNRES", "municipio", "regiao", "populacao"]]
    df = base.merge(nascimentos, on="CODMUNRES", how="left")
    df = df.merge(obitos, on="CODMUNRES", how="left")
    df["nascimentos"] = df["nascimentos"].fillna(0)
    df["obitos_infantis"] = df["obitos_infantis"].fillna(0)
    return df


def calcular_taxas(df):
    df["taxa_mortalidade_infantil"] = (
        df["obitos_infantis"] / df["nascimentos"].replace(0, pd.NA)
    ) * 1000
    df["taxa_natalidade"] = (
        df["nascimentos"] / df["populacao"].replace(0, pd.NA)
    ) * 1000
    return df


def agregar_regiao(df_municipio):
    por_regiao = df_municipio.groupby("regiao").agg(
        nascimentos=("nascimentos", "sum"),
        obitos_infantis=("obitos_infantis", "sum"),
        populacao=("populacao", "sum"),
    ).reset_index()
    return por_regiao


def salvar(df_municipio, df_regiao):
    OURO.mkdir(parents=True, exist_ok=True)
    destino_mun = OURO / "indicadores_municipio.parquet"
    destino_reg = OURO / "indicadores_regiao.csv"
    df_municipio.to_parquet(destino_mun, index=False)
    df_regiao.to_csv(destino_reg, index=False)
    print("salvo em:", destino_mun, df_municipio.shape)
    print("salvo em:", destino_reg, df_regiao.shape)
    return destino_mun, destino_reg


def registrar(destino_mun, destino_reg, decisoes):
    info = {
        "arquivos_ouro": [destino_mun.name, destino_reg.name],
        "decisoes": decisoes,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = OURO / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    sim, sinasc, populacao = carregar()
    obitos = obitos_infantis_por_municipio(sim)
    nascimentos = nascimentos_por_municipio(sinasc)
    obitos, nascimentos, populacao = preparar_chaves(obitos, nascimentos, populacao)
    checar_nao_casados("SINASC", nascimentos, populacao)
    checar_nao_casados("SIM (obitos infantis)", obitos, populacao)

    municipio = juntar_por_municipio(obitos, nascimentos, populacao)
    municipio = calcular_taxas(municipio)

    regiao = agregar_regiao(municipio)
    regiao = calcular_taxas(regiao)
    regiao = regiao.sort_values("taxa_mortalidade_infantil", ascending=False)

    print("\n=== Indicadores por regiao (2024) ===")
    print(regiao.to_string(index=False))

    destino_mun, destino_reg = salvar(municipio, regiao)
    registrar(destino_mun, destino_reg, [
        "obitos infantis = SIM com idade_anos == 0",
        "nascimentos = contagem de linhas do SINASC",
        "chave de juncao: CODMUNRES (DATASUS) == codigo_municipio_6 (IBGE, sem digito verificador)",
        "taxa_mortalidade_infantil = obitos_infantis / nascimentos * 1000 (por 1000 nascidos vivos)",
        "taxa_natalidade = nascimentos / populacao * 1000 (por 1000 habitantes)",
        "taxas por regiao calculadas somando numerador e denominador primeiro, dividindo depois (nao e' media das taxas municipais)",
    ])


if __name__ == "__main__":
    main()