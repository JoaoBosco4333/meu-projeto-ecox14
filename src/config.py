"""Configuracao central do projeto.

Entra aqui: caminhos, nomes de arquivo, parametros de fonte e a
configuracao do log. Nao entra: logica de transformacao nem segredos
(senha, token, chave), porque este arquivo vai para o GitHub.

Regra de importacao: este arquivo nao importa nenhum outro modulo do
projeto. Todos os outros podem importar config.
"""

import logging
from pathlib import Path

# Caminhos: calculados a partir deste arquivo, entao nao dependem de
# onde o comando foi executado (rodar de dentro de src deixa de quebrar).
RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
BRONZE = DADOS / "bronze"
PRATA = DADOS / "prata"
OURO = DADOS / "ouro"
LOG_ARQUIVO = RAIZ / "pipeline.log"

# Fontes baixadas a mao do portal de dados abertos do SUS. Ficam direto
# em dados/bronze/ e os scripts pegam sempre o arquivo mais recente.
SIM_PADRAO = "SIM_*.csv"
SINASC_PADRAO = "SINASC_*.csv"

# IBGE: populacao residente estimada por municipio (API de Agregados/SIDRA)
IBGE_AGREGADO = 6579
IBGE_VARIAVEL = 9324
IBGE_PERIODO = "2024"
IBGE_NIVEL = "N6[all]"  # N6 = municipio
IBGE_BRONZE = BRONZE / "ibge" / "populacao_municipios"
IBGE_PADRAO = "populacao_*.csv"
MUNICIPIOS_ESPERADOS = 5571  # 5.570 anteriores + Boa Esperanca do Norte (MT)


def configurar_log(nivel=logging.INFO):
    """Log na tela e no arquivo pipeline.log, ao mesmo tempo.

    O arquivo guarda a data completa (e nao so a hora) porque ele
    acumula varias execucoes: sem a data, nao da para saber qual
    execucao e qual.
    """
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_ARQUIVO, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
