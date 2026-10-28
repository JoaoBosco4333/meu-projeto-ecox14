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
from datetime import datetime
from pathlib import Path

import pandas as pd

PRATA = Path("dados/prata")

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
    print("cadastro (populacao):", cadastro.shape)
    print("chave unica no cadastro:", cadastro[CHAVE_CADASTRO].is_unique)
    return cadastro


def conferir_chaves(nome, fato, cadastro):
    """Passo 1: prever o que a juncao vai fazer, antes de juntar."""
    esq = set(fato[CHAVE_FATO].dropna().unique())
    dir_ = set(cadastro[CHAVE_CADASTRO].dropna().unique())
    so_cadastro = dir_ - esq

    print(f"\n--- {nome}: chaves antes de juntar ---")
    print("tipo da chave no", nome, ":", fato[CHAVE_FATO].dtype)
    print("tipo da chave no cadastro:", cadastro[CHAVE_CADASTRO].dtype)
    print("so no", nome, "    :", len(esq - dir_), "codigos")
    print("so no cadastro :", len(so_cadastro), "codigos")
    print("nos dois       :", len(esq & dir_), "codigos")
    print("linhas com chave vazia:", int(fato[CHAVE_FATO].isna().sum()))

    if so_cadastro:
        nomes = cadastro.loc[
            cadastro[CHAVE_CADASTRO].isin(list(so_cadastro)), "municipio"
        ]
        print("municipios do cadastro sem nenhum registro:", nomes.head(10).tolist())


def juntar(fato, cadastro):
    """Passo 2: left (nao perde linha do fato) + validate (avisa se o grao mudar)."""
    colisoes = set(fato.columns) & set(cadastro.columns)
    if colisoes:
        print("ATENCAO: colunas com o mesmo nome nas duas tabelas:", colisoes)
    return fato.merge(
        cadastro,
        left_on=CHAVE_FATO,
        right_on=CHAVE_CADASTRO,
        how="left",
        validate="many_to_one",
    )


def validar(nome, fato, resultado):
    """Passo 3: a conta que precisa fechar. Devolve quem nao casou."""
    sem_par = resultado[CHAVE_CADASTRO].isna()
    print(f"\n--- {nome}: validacao da juncao ---")
    print("antes     :", f"{len(fato):,}")
    print("resultado :", f"{len(resultado):,}")
    print("sem par   :", f"{int(sem_par.sum()):,}")
    if len(resultado) != len(fato):
        print("ATENCAO: o numero de linhas mudou.")
    return resultado[sem_par]


def descrever_sem_par(nome, sem_par):
    """Passo 4: quem nao casou e o achado. Mostra quais codigos sao."""
    if sem_par.empty:
        print(f"{nome}: todas as linhas casaram")
        return
    por_codigo = sem_par[CHAVE_FATO].value_counts(dropna=False)
    print(f"{nome}: {len(por_codigo)} codigo(s) sem par, em {len(sem_par):,} linhas.")
    print("os 10 codigos com mais linhas (<NA> = chave vazia):")
    print(por_codigo.head(10))


def mostrar_armadilha_do_grao(nome, resultado, cadastro):
    """Somar populacao depois da juncao repete cada municipio uma vez por
    linha do fato: o numero sai absurdo e nenhum erro aparece."""
    errada = int(resultado["populacao"].sum())
    certa = int(cadastro["populacao"].sum())
    print(f"\n--- {nome}: armadilha do grao ---")
    print("soma ERRADA (tabela enriquecida):", f"{errada:,}")
    print("soma CERTA  (cadastro)          :", f"{certa:,}")


def salvar(df, nome_arquivo):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / nome_arquivo
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
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


def enriquecer(nome, entrada, saida, cadastro):
    """Uma fonte de eventos (obito ou nascimento) + cadastro de municipios."""
    fato = pd.read_parquet(PRATA / entrada)
    print(f"\n##### {nome}: lido {entrada}", fato.shape)
    fato = normalizar_chave(fato, CHAVE_FATO)

    conferir_chaves(nome, fato, cadastro)
    resultado = juntar(fato, cadastro)
    sem_par = validar(nome, fato, resultado)
    descrever_sem_par(nome, sem_par)
    mostrar_armadilha_do_grao(nome, resultado, cadastro)

    destino = salvar(resultado, saida)
    registrar(entrada, destino, len(fato), len(resultado), len(sem_par), [
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
    fecha = int(no_municipio) == int(esperado)
    print(
        f"{rotulo}: municipio={int(no_municipio):,} | esperado={int(esperado):,}",
        "-> fecha" if fecha else "-> NAO FECHA",
    )


def previa_por_regiao(df):
    """So para olhar. Soma numerador e denominador no grao de municipio
    (correto) e so depois divide; nao e media das taxas municipais."""
    reg = df.groupby("regiao")[["populacao", "nascimentos", "obitos_infantis"]].sum()
    reg["taxa_natalidade"] = reg["nascimentos"] / reg["populacao"] * 1000
    reg["taxa_mortalidade_infantil"] = reg["obitos_infantis"] / reg["nascimentos"] * 1000
    print("\n=== previa por regiao (2024) ===")
    print(reg.round(2).to_string())


def main():
    cadastro = carregar_cadastro()

    sim = enriquecer("SIM", "sim.parquet", "sim_enriquecido.parquet", cadastro)
    infantis = sim[sim["idade_anos"] == 0]
    obitos = contar_por_municipio(infantis, "obitos_infantis")
    esperado_obitos = int(infantis[CHAVE_CADASTRO].notna().sum())
    del sim, infantis

    sinasc = enriquecer("SINASC", "sinasc.parquet", "sinasc_enriquecido.parquet", cadastro)
    nascimentos = contar_por_municipio(sinasc, "nascimentos")
    esperado_nasc = int(sinasc[CHAVE_CADASTRO].notna().sum())
    del sinasc

    municipio = montar_municipio(cadastro, nascimentos, obitos)
    municipio = calcular_taxas(municipio)

    print("\n--- conferindo se as contagens fecham ---")
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
    main()