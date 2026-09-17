"""Funcoes de limpeza que servem a qualquer fonte."""

import unicodedata

import pandas as pd


def tirar_espacos(df):
    df.columns = df.columns.str.strip()
    for c in df.select_dtypes(include="object"):
        df[c] = df[c].str.strip()
    return df


def chave_texto(serie):
    """Versao comparavel de um texto: sem acento,
    sem espaco sobrando e tudo em minuscula.
    Serve para comparar e juntar, nao para exibir."""
    s = serie.str.strip().str.lower()
    s = s.str.normalize("NFKD")
    s = s.str.encode("ascii", errors="ignore")
    return s.str.decode("utf-8")


def aplicar_mapa(serie, mapa):
    """Troca variantes pelo valor canonico.
    O que nao estiver no mapa fica como esta."""
    return serie.replace(mapa)


def tipar_categoria_ordenada(df, coluna, categorias):
    """Declara uma coluna como categoria com ordem. Valores fora
    da lista viram ausentes - e isso fica registrado no print."""
    antes = df[coluna].isna().sum()
    df[coluna] = pd.Categorical(df[coluna], categories=categorias, ordered=True)
    depois = df[coluna].isna().sum()
    print(coluna, "fora da escala (viraram ausente):", depois - antes)
    return df

def faixa_por_corte(df, coluna, cortes, rotulos):
    """Cria uma coluna de faixa a partir de cortes de valor fixos
    (nao por quantil) - usa quando existe um limiar real do dominio,
    nao um recorte estatistico."""
    nova = coluna + "_faixa"
    df[nova] = pd.cut(df[coluna], bins=cortes, labels=rotulos)
    print(nova, "distribuicao:")
    print(df[nova].value_counts(dropna=False))
    return df