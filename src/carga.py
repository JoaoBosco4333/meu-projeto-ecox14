"""Carga: carrega a Prata dentro de um banco DuckDB.

A camada Ouro NAO e mais construida aqui: desde a Aula 10 quem a constroi e o
dbt (pasta ecox14/, etapa modelagem do pipeline). Este arquivo continua com
tudo que nao e transformacao: abrir o banco, ler os Parquets e conferir.

O banco inteiro e um arquivo so: dados/ouro/projeto.duckdb. Apagar o arquivo
e uma forma legitima de recomecar do zero; rodar de novo tambem e seguro
(CREATE OR REPLACE refaz cada tabela, sem duplicar nada).

Esquemas dentro do banco:
    prata -> os Parquets da Prata, como estao (criado por este arquivo)
    ouro  -> nasce da prata, aqui dentro, construido pelo dbt

Modelo da Ouro (esquema estrela), definido em ecox14/models/:
    ouro.dim_municipio             1 linha = 1 municipio              (dimensao)
    ouro.fato_indicador_municipio  1 linha = 1 municipio em 1 ano     (fato)
    ouro.vw_indicador_completo     view: fato + dimensao (tabela achatada)
    ouro.vw_indicador_regiao       view: 1 linha = 1 regiao em 1 ano

Como executar, a partir de qualquer pasta:
    python src/carga.py             # so a carga da Prata
    python src/pipeline.py carga    # carga + modelagem (dbt) + conferencia
"""

import logging

import duckdb

from config import MUNICIPIOS_ESPERADOS, OURO, PRATA, configurar_log

log = logging.getLogger("carga")

BANCO = OURO / "projeto.duckdb"

# Parquets da Prata que entram no banco (nome da tabela = nome do arquivo).
# sim.parquet e sinasc.parquet ficam de fora de proposito: as versoes
# enriquecidas tem as mesmas linhas e as mesmas colunas, mais 4. Carregar as
# duas seria guardar tudo duas vezes (o banco passaria de ~330 MB para ~630 MB).
# Para incluir, e so acrescentar "sim" e "sinasc" nesta lista.
TABELAS_PRATA = [
    "populacao",
    "sim_enriquecido",
    "sinasc_enriquecido",
    "municipio_enriquecido",
]


def um_valor(con, sql):
    """Roda uma consulta que devolve uma celula so e devolve o valor.
    Usa con.execute e nao con.sql: o objeto de con.sql nem sempre tem fetchone."""
    return con.execute(sql).fetchone()[0]


def contar(con, tabela):
    return um_valor(con, f"SELECT COUNT(*) FROM {tabela}")


def criar_esquemas(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS prata")
    con.execute("CREATE SCHEMA IF NOT EXISTS ouro")


def conectar():
    """Abre o arquivo do banco (cria se nao existir) e garante os dois esquemas."""
    OURO.mkdir(parents=True, exist_ok=True)
    try:
        con = duckdb.connect(str(BANCO))
    except duckdb.IOException:
        log.error("nao foi possivel abrir %s: outro programa esta com o banco aberto? "
                  "(extensao do VS Code, DBeaver, outro terminal). Feche e rode de novo.",
                  BANCO)
        raise
    criar_esquemas(con)
    log.info("banco aberto: %s", BANCO)
    return con


def carregar_prata(con):
    """Passo 3: cada Parquet da Prata vira uma tabela do esquema prata.
    O DuckDB le o Parquet direto, sem etapa de importacao, e os tipos
    (numero, data, texto) ja vem certos porque a Prata foi gravada em Parquet."""
    for nome in TABELAS_PRATA:
        caminho = PRATA / f"{nome}.parquet"
        if not caminho.exists():
            raise FileNotFoundError(
                f"{caminho} nao existe. Rode as etapas anteriores: "
                f"python src/pipeline.py transformacao"
            )
        # as_posix troca a barra invertida do Windows pela barra comum,
        # que e o que o SQL espera dentro de uma string.
        con.execute(f"""
            CREATE OR REPLACE TABLE prata.{nome} AS
            SELECT * FROM read_parquet('{caminho.as_posix()}')
        """)
        log.info("prata.%s: %s linhas", nome, f"{contar(con, 'prata.' + nome):,}")


def construir_ouro(con):
    """APOSENTADA na Aula 10: hoje a Ouro e construida pelo dbt (ecox14/models),
    com o mesmo SQL, um arquivo por tabela. Fica aqui, sem ser chamada, para
    comparar os dois jeitos e mostrar de onde os modelos do dbt vieram."""

    # Dimensao: o que DESCREVE o municipio (palavras pelas quais se agrupa/filtra).
    # O nome da fonte traz a UF no fim ("Ariquemes - RO"); aqui ela vira coluna propria.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_municipio AS
        SELECT
            codigo_municipio_6                              AS municipio_id,
            codigo_municipio                                AS codigo_ibge,
            regexp_replace(municipio, ' - [A-Z]{2}$', '')   AS nome,
            regexp_extract(municipio, ' - ([A-Z]{2})$', 1)  AS uf,
            regiao
        FROM prata.populacao
    """)
    log.info("ouro.dim_municipio: %s linhas", f"{contar(con, 'ouro.dim_municipio'):,}")

    # Fato: o que SE MEDE. Grao: 1 municipio em 1 ano.
    # A origem e o municipio_enriquecido (ja resolveu quem tem municipio no cadastro);
    # o ano vem da populacao (ano de referencia da estimativa do IBGE).
    # Populacao, nascimentos e obitos_infantis podem ser somados entre municipios;
    # as taxas NAO (para somar por regiao, soma-se numerador e denominador e divide-se depois).
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_indicador_municipio AS
        SELECT
            m.codigo_municipio_6        AS municipio_id,
            p.ano                       AS ano,
            m.populacao                 AS populacao,
            m.nascimentos               AS nascimentos,
            m.obitos_infantis           AS obitos_infantis,
            m.taxa_natalidade           AS taxa_natalidade,
            m.taxa_mortalidade_infantil AS taxa_mortalidade_infantil
        FROM prata.municipio_enriquecido m
        LEFT JOIN prata.populacao p USING (codigo_municipio_6)
        WHERE m.codigo_municipio_6 IS NOT NULL
    """)
    log.info("ouro.fato_indicador_municipio: %s linhas",
             f"{contar(con, 'ouro.fato_indicador_municipio'):,}")

    # View: a tabela achatada como consulta salva. Nao guarda dado: o banco
    # refaz o join na hora, entao nunca fica desatualizada.
    con.execute("""
        CREATE OR REPLACE VIEW ouro.vw_indicador_completo AS
        SELECT f.*, d.nome, d.uf, d.regiao
        FROM ouro.fato_indicador_municipio f
        JOIN ouro.dim_municipio d USING (municipio_id)
    """)

    # View: a resposta da pergunta, por regiao e ano. Soma numerador e
    # denominador no grao de municipio e so depois divide (nao e media de taxas).
    con.execute("""
        CREATE OR REPLACE VIEW ouro.vw_indicador_regiao AS
        SELECT
            regiao,
            ano,
            CAST(SUM(populacao) AS BIGINT)                    AS populacao,
            CAST(SUM(nascimentos) AS BIGINT)                  AS nascimentos,
            CAST(SUM(obitos_infantis) AS BIGINT)              AS obitos_infantis,
            SUM(nascimentos) * 1000.0 / SUM(populacao)        AS taxa_natalidade,
            SUM(obitos_infantis) * 1000.0 / SUM(nascimentos)  AS taxa_mortalidade_infantil
        FROM ouro.vw_indicador_completo
        GROUP BY regiao, ano
    """)
    log.info("views criadas: ouro.vw_indicador_completo, ouro.vw_indicador_regiao")


def exigir(rotulo, obtido, esperado):
    """A conta que fecha. Se nao fecha, o pipeline para (mesma regra do enriquecimento)."""
    obtido, esperado = int(obtido or 0), int(esperado or 0)
    if obtido != esperado:
        log.error("%s: obtido=%s | esperado=%s -> NAO FECHA",
                  rotulo, f"{obtido:,}", f"{esperado:,}")
        raise ValueError(f"conferencia da carga falhou: {rotulo}")
    log.info("%s: %s -> ok", rotulo, f"{obtido:,}")


def conferir(con):
    """Passo 7: prova que o modelo esta de pe. Cada verificacao para o pipeline se falhar."""
    log.info("--- conferindo o modelo ---")

    # O grao se confirma? (nenhum municipio aparece duas vezes no mesmo ano)
    exigir("fato: municipios repetidos no mesmo ano", um_valor(con, """
        SELECT COUNT(*) FROM (
            SELECT municipio_id, ano FROM ouro.fato_indicador_municipio
            GROUP BY municipio_id, ano HAVING COUNT(*) > 1
        )"""), 0)

    # Sobrou fato sem dimensao? (fato orfao)
    exigir("fato: linhas sem municipio na dimensao", um_valor(con, """
        SELECT COUNT(*) FROM ouro.fato_indicador_municipio f
        LEFT JOIN ouro.dim_municipio d USING (municipio_id)
        WHERE d.municipio_id IS NULL"""), 0)

    exigir("fato: linhas sem ano", um_valor(con,
        "SELECT COUNT(*) FROM ouro.fato_indicador_municipio WHERE ano IS NULL"), 0)

    # A dimensao tem 1 linha por municipio, e todos tem regiao.
    n_dim = contar(con, "ouro.dim_municipio")
    exigir("dim_municipio: linhas (esperado = municipios do IBGE)", n_dim, MUNICIPIOS_ESPERADOS)
    exigir("dim_municipio: municipio_id repetido", n_dim - um_valor(con,
        "SELECT COUNT(DISTINCT municipio_id) FROM ouro.dim_municipio"), 0)
    exigir("dim_municipio: municipios sem regiao", um_valor(con,
        "SELECT COUNT(*) FROM ouro.dim_municipio WHERE regiao IS NULL"), 0)

    # Nenhuma linha se perdeu entre a Prata, a fato e as views.
    n_fato = contar(con, "ouro.fato_indicador_municipio")
    exigir("fato = municipio_enriquecido (linhas)", n_fato,
           contar(con, "prata.municipio_enriquecido"))
    exigir("vw_indicador_completo = fato (linhas)",
           contar(con, "ouro.vw_indicador_completo"), n_fato)

    # As contagens da Ouro batem com os eventos da Prata (a conta que fecha).
    exigir("nascimentos: fato = linhas do sinasc_enriquecido com municipio",
           um_valor(con, "SELECT SUM(nascimentos) FROM ouro.fato_indicador_municipio"),
           um_valor(con, "SELECT COUNT(*) FROM prata.sinasc_enriquecido "
                         "WHERE codigo_municipio_6 IS NOT NULL"))
    exigir("obitos infantis: fato = linhas do sim_enriquecido (idade 0) com municipio",
           um_valor(con, "SELECT SUM(obitos_infantis) FROM ouro.fato_indicador_municipio"),
           um_valor(con, "SELECT COUNT(*) FROM prata.sim_enriquecido "
                         "WHERE idade_anos = 0 AND codigo_municipio_6 IS NOT NULL"))

    # Quem ficou de fora da fato (municipio ignorado, UF+0000): so informativo.
    sem_nasc = um_valor(con, "SELECT COUNT(*) FROM prata.sinasc_enriquecido "
                             "WHERE codigo_municipio_6 IS NULL")
    sem_obito = um_valor(con, "SELECT COUNT(*) FROM prata.sim_enriquecido "
                              "WHERE idade_anos = 0 AND codigo_municipio_6 IS NULL")
    log.info("fora da fato (municipio ignorado, UF+0000): %s nascimentos e %s obitos infantis; "
             "continuam em prata.sinasc_enriquecido e prata.sim_enriquecido",
             f"{sem_nasc:,}", f"{sem_obito:,}")


def mostrar_regioes(con):
    """So para olhar: a resposta da pergunta, lida da view da Ouro."""
    df = con.execute("""
        SELECT
            regiao,
            ano,
            populacao,
            nascimentos,
            obitos_infantis,
            ROUND(taxa_natalidade, 2)           AS taxa_natalidade,
            ROUND(taxa_mortalidade_infantil, 2) AS taxa_mortalidade_infantil
        FROM ouro.vw_indicador_regiao
        ORDER BY taxa_mortalidade_infantil DESC
    """).df()
    log.info("=== ouro.vw_indicador_regiao ===\n%s", df.to_string(index=False))


def main():
    con = conectar()
    try:
        carregar_prata(con)
        # construir_ouro(con)  <- agora e o dbt (etapa modelagem)
        # conferir(con)        <- agora roda DEPOIS do dbt: ver conferir_ouro()
    finally:
        # Libera o arquivo. Tem que fechar aqui: o dbt roda logo depois, em outro
        # programa, e dois programas abertos no mesmo arquivo dao "file is locked".
        con.close()


def conferir_ouro():
    """Roda depois do dbt: so ai a Ouro existe. Se algo nao fecha, levanta erro
    e o pipeline para. (Na proxima aula estas contas viram testes do dbt.)"""
    con = conectar()
    try:
        conferir(con)
        mostrar_regioes(con)
    finally:
        con.close()


if __name__ == "__main__":
    configurar_log()
    main()
