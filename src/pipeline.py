"""Pipeline completo: ingestao -> transformacao -> enriquecimento -> carga -> modelagem.

Como executar, a partir de qualquer pasta:
    python src/pipeline.py                  # roda tudo
    python src/pipeline.py enriquecimento   # retoma a partir de uma etapa
    python src/pipeline.py carga            # a carga (e o que vier depois dela)
    python src/pipeline.py modelagem        # so o dbt, que reconstroi a camada Ouro

A modelagem roda o dbt (projeto em ecox14/) e depois confere o resultado. Uma
etapa que esteja com None na lista e apenas registrada no log, sem quebrar a
execucao (serve para etapas ainda nao implementadas).

Regra de importacao: o pipeline importa as etapas; nenhuma etapa importa
o pipeline.
"""

import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

import config
import enriquecer
import ingerir_ibge_populacao
import transformar_populacao
import transformar_sim
import transformar_sinasc

log = logging.getLogger("pipeline")


def conferir_fontes_manuais():
    """SIM e SINASC sao baixados a mao. Se faltarem, para cedo e explica."""
    for rotulo, padrao in (("SIM", config.SIM_PADRAO), ("SINASC", config.SINASC_PADRAO)):
        arquivos = sorted(config.BRONZE.glob(padrao))
        if not arquivos:
            raise FileNotFoundError(
                f"fonte {rotulo} ausente: nenhum arquivo '{padrao}' em {config.BRONZE}. "
                f"Baixe do portal de dados abertos do SUS (veja o README)."
            )
        arquivo = arquivos[-1]
        log.info("fonte %s encontrada: %s (%.0f MB)",
                 rotulo, arquivo.name, arquivo.stat().st_size / 1e6)


def ingerir_todas():
    conferir_fontes_manuais()
    ingerir_ibge_populacao.main()


def transformar_todas():
    transformar_populacao.main()
    transformar_sim.main()
    transformar_sinasc.main()


def etapa_carga():
    # O import fica dentro da funcao: se o duckdb nao estiver instalado, o erro
    # aparece so quando a carga roda; as etapas anteriores nao dependem dele.
    import carga
    carga.main()


def etapa_modelagem():
    # O dbt constroi a Ouro (dim, fato e views) dentro do banco que a carga criou.
    # Procura o dbt na mesma pasta do Python que esta rodando o pipeline; assim
    # funciona mesmo sem ativar o ambiente virtual (se nao achar, tenta o PATH).
    dbt = shutil.which("dbt", path=str(Path(sys.executable).parent)) or shutil.which("dbt")
    if dbt is None:
        raise FileNotFoundError("dbt nao encontrado. Instale com: pip install -r requirements.txt")
    resultado = subprocess.run(
        [dbt, "--no-use-colors", "run"],
        cwd=config.RAIZ / "ecox14",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # A saida do dbt entra no log do pipeline, para o erro (se houver) ficar la.
    for linha in resultado.stdout.splitlines():
        if linha.strip():
            log.info("dbt: %s", linha)
    # Se o dbt falhou, levanta erro. Sem isso o pipeline diria que terminou
    # bem com a Ouro quebrada.
    resultado.check_returncode()

    import carga
    carga.conferir_ouro()


ETAPAS = [
    ("ingestao", ingerir_todas),
    ("transformacao", transformar_todas),
    ("enriquecimento", enriquecer.main),
    ("carga", etapa_carga),
    ("modelagem", etapa_modelagem),
]


def executar(nome, funcao):
    inicio = time.perf_counter()
    log.info("etapa %s: inicio", nome)
    try:
        funcao()
    except Exception:
        log.exception("etapa %s: FALHOU", nome)
        raise
    log.info("etapa %s: fim em %.0fs", nome, time.perf_counter() - inicio)


def main(a_partir_de=None):
    config.configurar_log()

    nomes = [nome for nome, _ in ETAPAS]
    if a_partir_de is not None and a_partir_de not in nomes:
        log.error("etapa desconhecida: '%s'. Opcoes: %s", a_partir_de, ", ".join(nomes))
        sys.exit(1)

    log.info("inicio (a partir de: %s)", a_partir_de or "o comeco")
    inicio = time.perf_counter()
    retomando = a_partir_de is not None

    for nome, funcao in ETAPAS:
        if retomando and nome != a_partir_de:
            log.info("etapa %s: pulada (antes do ponto de retomada)", nome)
            continue
        retomando = False

        if funcao is None:
            log.info("etapa %s: ainda nao implementada", nome)
            continue
        executar(nome, funcao)

    log.info("fim em %.0fs", time.perf_counter() - inicio)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
