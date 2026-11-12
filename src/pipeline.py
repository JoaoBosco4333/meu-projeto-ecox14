"""Pipeline completo: ingestao -> transformacao -> enriquecimento -> carga.

Como executar, a partir de qualquer pasta:
    python src/pipeline.py                  # roda tudo
    python src/pipeline.py enriquecimento   # retoma a partir de uma etapa
    python src/pipeline.py carga            # so a carga (e o que vier depois dela)

Etapas ainda nao implementadas (modelagem) aparecem na lista com None e
sao apenas registradas no log, sem quebrar a execucao.

Regra de importacao: o pipeline importa as etapas; nenhuma etapa importa
o pipeline.
"""

import logging
import sys
import time

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


ETAPAS = [
    ("ingestao", ingerir_todas),
    ("transformacao", transformar_todas),
    ("enriquecimento", enriquecer.main),
    ("carga", etapa_carga),
    ("modelagem", None),
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
