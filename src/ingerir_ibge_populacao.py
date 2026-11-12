"""
Ingestao da terceira fonte: populacao residente estimada por municipio,
IBGE (API de Agregados / SIDRA).

Agregado 6579 = "Populacao residente estimada"
Variavel  9324 = "Populacao residente estimada (Pessoas)"
Nivel territorial N6 = municipio

Os parametros (agregado, variavel, periodo, pasta) ficam no config.py.

Como executar, a partir da raiz do projeto:
    python src/ingerir_ibge_populacao.py
"""

import json
import logging
from datetime import date, datetime

import pandas as pd
import requests

from config import (
    IBGE_AGREGADO,
    IBGE_BRONZE,
    IBGE_NIVEL,
    IBGE_PERIODO,
    IBGE_VARIAVEL,
    MUNICIPIOS_ESPERADOS,
    configurar_log,
)

log = logging.getLogger("ingerir_ibge_populacao")

URL = (
    f"https://servicodados.ibge.gov.br/api/v3/agregados/"
    f"{IBGE_AGREGADO}/periodos/{IBGE_PERIODO}/variaveis/{IBGE_VARIAVEL}"
)


def buscar():
    log.info("consultando a API do IBGE (agregado %s, periodo %s)", IBGE_AGREGADO, IBGE_PERIODO)
    resposta = requests.get(URL, params={"localidades": IBGE_NIVEL}, timeout=60)
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
    if encontrados != MUNICIPIOS_ESPERADOS:
        log.warning(
            "municipios recebidos: %d, esperados: %d (confira o config.py)",
            encontrados, MUNICIPIOS_ESPERADOS,
        )
    else:
        log.info("municipios recebidos: %d", encontrados)
    return encontrados


def salvar(df):
    IBGE_BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = IBGE_BRONZE / f"populacao_{hoje}.csv"
    df.to_csv(destino, index=False)
    log.info("salvo em: %s %s", destino, df.shape)
    return destino


def registrar(destino, encontrados):
    info = {
        "fonte": URL,
        "agregado": IBGE_AGREGADO,
        "variavel": IBGE_VARIAVEL,
        "periodo": IBGE_PERIODO,
        "arquivo_bronze": destino.name,
        "municipios_recebidos": int(encontrados),
        "municipios_esperados": MUNICIPIOS_ESPERADOS,
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = IBGE_BRONZE / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    log.info("proveniencia: %s", caminho)


def main():
    dados = buscar()
    df = achatar(dados)
    encontrados = conferir(df)
    destino = salvar(df)
    registrar(destino, encontrados)


if __name__ == "__main__":
    configurar_log()
    main()