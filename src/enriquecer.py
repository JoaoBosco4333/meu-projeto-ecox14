"""Enriquecimento (Prata): junta SIM e SINASC ao cadastro de municipios
(tabela de populacao do IBGE) pela chave do municipio de residencia.

Grao (o que e uma linha) em cada tabela:
    sim, sinasc  -> 1 obito / 1 nascimento      (lado "muitos")
    populacao    -> 1 municipio                 (lado "um")
    resultado    -> o mesmo grao do sim / sinasc, com municipio,
                    regiao e populacao acrescentados

Como executar, a partir da raiz do projeto:
    python src/enriquecer.py
"""

import json
import logging
from datetime import datetime

import pandas as pd

from config import PRATA, configurar_log

log = logging.getLogger("enriquecer")

CHAVE_FATO = "CODMUNRES"               # DATASUS: 6 digitos
CHAVE_CADASTRO = "codigo_municipio_6"  # IBGE sem o digito verificador
COLUNAS_CADASTRO = [CHAVE_CADASTRO, "municipio", "regiao", "populacao"]


def normalizar_chave(df, coluna):
    """Garante o mesmo tipo dos dois lados antes de juntar."""
    df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype("Int64")
    return df


def carregar_cadastro():
    cadastro = pd.read_parquet(PRATA / "populacao.parquet", columns=COLUNAS_CADASTRO)
    cadastro = normalizar_chave(cadastro, CHAVE_CADASTRO)
    log.info("cadastro (populacao): %s", cadastro.shape)
    if not cadastro[CHAVE_CADASTRO].is_unique:
        log.warning("chave NAO e unica no cadastro: a juncao vai falhar no validate")
    else:
        log.info("chave unica no cadastro: True")
    return cadastro


def conferir_chaves(nome, fato, cadastro):
    """Passo 1: prever o que a juncao vai fazer, antes de juntar."""
    esq = set(fato[CHAVE_FATO].dropna().unique())
    dir_ = set(cadastro[CHAVE_CADASTRO].dropna().unique())
    so_cadastro = dir_ - esq

    log.info("--- %s: chaves antes de juntar ---", nome)
    log.info("tipo da chave no %s: %s", nome, fato[CHAVE_FATO].dtype)
    log.info("tipo da chave no cadastro: %s", cadastro[CHAVE_CADASTRO].dtype)
    log.info("so no %s: %d codigos", nome, len(esq - dir_))
    log.info("so no cadastro: %d codigos", len(so_cadastro))
    log.info("nos dois: %d codigos", len(esq & dir_))
    log.info("linhas com chave vazia: %d", int(fato[CHAVE_FATO].isna().sum()))

    if so_cadastro:
        nomes = cadastro.loc[
            cadastro[CHAVE_CADASTRO].isin(list(so_cadastro)), "municipio"
        ]
        log.info("municipios do cadastro sem nenhum registro (10 primeiros): %s",
                 nomes.head(10).tolist())


def juntar(fato, cadastro):
    """Passo 2: left (nao perde linha do fato) + validate (avisa se o grao mudar).

    Para nao duplicar o DataFrame na memoria, a juncao roda so sobre a coluna
    da chave; as colunas do cadastro que voltam sao acrescentadas ao proprio
    fato. O resultado e o de fato.merge(cadastro, ...): mesmas linhas, na
    mesma ordem, com as colunas do cadastro no final.
    """
    colisoes = set(fato.columns) & set(cadastro.columns)
    if colisoes:
        log.warning("colunas com o mesmo nome nas duas tabelas: %s", colisoes)
    ligacao = fato[[CHAVE_FATO]].merge(
        cadastro,
        left_on=CHAVE_FATO,
        right_on=CHAVE_CADASTRO,
        how="left",
        validate="many_to_one",
    )
    if len(ligacao) != len(fato):
        log.error("a juncao mudou o numero de linhas: %d -> %d", len(fato), len(ligacao))
        raise ValueError("a juncao mudou o numero de linhas")
    ligacao.index = fato.index
    for coluna in cadastro.columns:
        fato[coluna] = ligacao[coluna]
    return fato


def validar(nome, linhas_antes, resultado):
    """Passo 3: a conta que precisa fechar. Devolve quem nao casou."""
    sem_par = resultado[CHAVE_CADASTRO].isna()
    log.info("--- %s: validacao da juncao ---", nome)
    log.info("antes: %s | resultado: %s | sem par: %s",
             f"{linhas_antes:,}", f"{len(resultado):,}", f"{int(sem_par.sum()):,}")
    if len(resultado) != linhas_antes:
        log.error("%s: o numero de linhas mudou na juncao", nome)
        raise ValueError(f"{nome}: a juncao mudou o numero de linhas")
    return resultado[sem_par]


def descrever_sem_par(nome, sem_par):
    """Passo 4: quem nao casou e o achado. Mostra quais codigos sao."""
    if sem_par.empty:
        log.info("%s: todas as linhas casaram", nome)
        return
    por_codigo = sem_par[CHAVE_FATO].value_counts(dropna=False)
    log.warning(
        "%s: %d codigo(s) sem par, em %s linhas "
        "(esperado: codigos UF+0000 = municipio ignorado)",
        nome, len(por_codigo), f"{len(sem_par):,}",
    )
    log.info("os 10 codigos com mais linhas (<NA> = chave vazia):\n%s",
             por_codigo.head(10).to_string())


def mostrar_armadilha_do_grao(nome, resultado, cadastro):
    """Somar populacao depois da juncao repete cada municipio uma vez por
    linha do fato: o numero sai absurdo e nenhum erro aparece."""
    errada = int(resultado["populacao"].sum())
    certa = int(cadastro["populacao"].sum())
    log.info("--- %s: armadilha do grao ---", nome)
    log.info("soma ERRADA (tabela enriquecida): %s", f"{errada:,}")
    log.info("soma CERTA  (cadastro)          : %s", f"{certa:,}")


def salvar(df, nome_arquivo):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / nome_arquivo
    df.to_parquet(destino, index=False)
    log.info("salvo em: %s %s", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, sem_par, decisoes):
    info = {
        "origem": origem,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "sem_par": sem_par,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def enriquecer_fonte(nome, entrada, saida, cadastro):
    """Uma fonte de eventos (obito ou nascimento) + cadastro de municipios."""
    fato = pd.read_parquet(PRATA / entrada)
    log.info("##### %s: lido %s %s", nome, entrada, fato.shape)
    fato = normalizar_chave(fato, CHAVE_FATO)
    linhas_antes = len(fato)

    conferir_chaves(nome, fato, cadastro)
    resultado = juntar(fato, cadastro)
    sem_par = validar(nome, linhas_antes, resultado)
    descrever_sem_par(nome, sem_par)
    mostrar_armadilha_do_grao(nome, resultado, cadastro)

    destino = salvar(resultado, saida)
    registrar(entrada, destino, linhas_antes, len(resultado), len(sem_par), [
        "CODMUNRES convertida para Int64 (mesmo tipo do cadastro)",
        "juncao left com validate=many_to_one: CODMUNRES = codigo_municipio_6",
        "colunas acrescentadas: municipio, regiao, populacao",
        "linhas sem par mantidas na tabela, com municipio/regiao/populacao ausentes",
    ])
    return resultado


def contar_por_municipio(df, nome_coluna):
    """Agrega: 1 linha = 1 municipio. O grao muda de proposito.
    Linhas sem par ficam de fora (nao ha municipio para atribuir)."""
    return (
        df.dropna(subset=[CHAVE_CADASTRO])
        .groupby(CHAVE_CADASTRO)
        .size()
        .rename(nome_coluna)
        .reset_index()
    )


def montar_municipio(cadastro, nascimentos, obitos):
    """Cadastro (1 linha por municipio) + contagens (1 linha por municipio)."""
    df = cadastro.merge(
        nascimentos, on=CHAVE_CADASTRO, how="left", validate="one_to_one"
    )
    df = df.merge(obitos, on=CHAVE_CADASTRO, how="left", validate="one_to_one")
    # municipio sem nenhuma linha na fonte = zero ocorrencias registradas
    df["nascimentos"] = df["nascimentos"].fillna(0).astype("int64")
    df["obitos_infantis"] = df["obitos_infantis"].fillna(0).astype("int64")
    return df


def calcular_taxas(df):
    """Atributos que so existem depois da juncao: dependem da populacao
    (IBGE) e das contagens (DATASUS) na mesma linha."""
    pop = df["populacao"].astype("float64")
    nasc = df["nascimentos"].astype("float64")
    obi = df["obitos_infantis"].astype("float64")
    df["taxa_natalidade"] = nasc / pop.where(pop > 0) * 1000
    df["taxa_mortalidade_infantil"] = obi / nasc.where(nasc > 0) * 1000
    return df


def conferir_total(rotulo, no_municipio, esperado):
    """A conta que fecha. Se nao fecha, o pipeline para: nao adianta
    seguir adiante com taxas calculadas sobre contagens erradas."""
    no_municipio, esperado = int(no_municipio), int(esperado)
    if no_municipio != esperado:
        log.error("%s: municipio=%s | esperado=%s -> NAO FECHA",
                  rotulo, f"{no_municipio:,}", f"{esperado:,}")
        raise ValueError(f"contagem de {rotulo} nao fecha")
    log.info("%s: municipio=%s | esperado=%s -> fecha",
             rotulo, f"{no_municipio:,}", f"{esperado:,}")


def previa_por_regiao(df):
    """So para olhar. Soma numerador e denominador no grao de municipio
    (correto) e so depois divide; nao e media das taxas municipais."""
    reg = df.groupby("regiao")[["populacao", "nascimentos", "obitos_infantis"]].sum()
    reg["taxa_natalidade"] = reg["nascimentos"] / reg["populacao"] * 1000
    reg["taxa_mortalidade_infantil"] = reg["obitos_infantis"] / reg["nascimentos"] * 1000
    log.info("=== previa por regiao (2024) ===\n%s", reg.round(2).to_string())


def main():
    cadastro = carregar_cadastro()

    sim = enriquecer_fonte("SIM", "sim.parquet", "sim_enriquecido.parquet", cadastro)
    infantis = sim[sim["idade_anos"] == 0]
    obitos = contar_por_municipio(infantis, "obitos_infantis")
    esperado_obitos = int(infantis[CHAVE_CADASTRO].notna().sum())
    del sim, infantis

    sinasc = enriquecer_fonte("SINASC", "sinasc.parquet", "sinasc_enriquecido.parquet", cadastro)
    nascimentos = contar_por_municipio(sinasc, "nascimentos")
    esperado_nasc = int(sinasc[CHAVE_CADASTRO].notna().sum())
    del sinasc

    municipio = montar_municipio(cadastro, nascimentos, obitos)
    municipio = calcular_taxas(municipio)

    log.info("--- conferindo se as contagens fecham ---")
    conferir_total("nascimentos", municipio["nascimentos"].sum(), esperado_nasc)
    conferir_total("obitos infantis", municipio["obitos_infantis"].sum(), esperado_obitos)

    previa_por_regiao(municipio)
    destino = salvar(municipio, "municipio_enriquecido.parquet")
    registrar("sim_enriquecido + sinasc_enriquecido + populacao", destino,
              len(cadastro), len(municipio), 0, [
        "1 linha = 1 municipio (grao muda de proposito: contagens por municipio)",
        "nascimentos = linhas do sinasc_enriquecido com municipio casado",
        "obitos_infantis = linhas do sim_enriquecido com idade_anos == 0 e municipio casado",
        "municipio sem linhas na fonte recebe 0 (contagem)",
        "taxa_natalidade = nascimentos / populacao * 1000",
        "taxa_mortalidade_infantil = obitos_infantis / nascimentos * 1000",
    ])


if __name__ == "__main__":
    configurar_log()
    main()