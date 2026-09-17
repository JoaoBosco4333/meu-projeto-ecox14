"""
Ingestao da terceira fonte: populacao residente estimada por municipio,
IBGE (API de Agregados / SIDRA).

Agregado 6579 = "Populacao residente estimada"
Variavel  9324 = "Populacao residente estimada (Pessoas)"
Nivel territorial N6 = municipio

Como executar, a partir da raiz do projeto:
    python src/ingerir_ibge_populacao.py
"""

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

AGREGADO = 6579
VARIAVEL = 9324
PERIODO = "2024"
NIVEL = "N6[all]"  # todos os municipios

URL = (
    f"https://servicodados.ibge.gov.br/api/v3/agregados/"
    f"{AGREGADO}/periodos/{PERIODO}/variaveis/{VARIAVEL}"
)

BRONZE = Path("dados/bronze/ibge/populacao_municipios")
MUNICIPIOS_ESPERADOS = 5570  # numero oficial de municipios brasileiros


def buscar():
    resposta = requests.get(URL, params={"localidades": NIVEL}, timeout=60)
    resposta.raise_for_status()
    return resposta.json()


def achatar(dados):
    """Desmonta a resposta aninhada do SIDRA: uma linha por municipio."""
    variavel = dados[0]
    registros = []
    for resultado in variavel["resultados"]:
        for serie in resultado["series"]:
            municipio_id = serie["localidade"]["id"]
            municipio_nome = serie["localidade"]["nome"]
            for ano, valor in serie["serie"].items():
                registros.append({
                    "codigo_municipio": municipio_id,
                    "municipio": municipio_nome,
                    "ano": ano,
                    "populacao": valor,
                })
    return pd.DataFrame(registros)


def conferir(df):
    encontrados = df["codigo_municipio"].nunique()
    print("municipios recebidos:", encontrados)
    if encontrados < MUNICIPIOS_ESPERADOS:
        print(f"ATENCAO: recebido menos municipios que o esperado ({MUNICIPIOS_ESPERADOS}).")
    return encontrados


def salvar(df):
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"populacao_{hoje}.csv"
    df.to_csv(destino, index=False)
    print("formato:", df.shape)
    print("salvo em:", destino)
    return destino


def registrar(destino, encontrados):
    info = {
        "fonte": URL,
        "agregado": AGREGADO,
        "variavel": VARIAVEL,
        "periodo": PERIODO,
        "arquivo_bronze": destino.name,
        "municipios_recebidos": int(encontrados),
        "municipios_esperados": MUNICIPIOS_ESPERADOS,
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = BRONZE / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    print("proveniencia:", caminho)


def main():
    dados = buscar()
    df = achatar(dados)
    encontrados = conferir(df)
    destino = salvar(df)
    registrar(destino, encontrados)


if __name__ == "__main__":
    main()