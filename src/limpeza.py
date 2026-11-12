"""Funcoes de limpeza que servem a qualquer fonte.

Regra de importacao: este modulo nao importa nenhuma etapa do pipeline,
so bibliotecas. Quem esta embaixo nao sabe que quem esta em cima existe.
"""

import logging
import unicodedata

import numpy as np
import pandas as pd
from pandas.api.types import union_categoricals

log = logging.getLogger("limpeza")


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
    da lista viram ausentes - e isso fica registrado no log."""
    antes = df[coluna].isna().sum()
    df[coluna] = pd.Categorical(df[coluna], categories=categorias, ordered=True)
    depois = df[coluna].isna().sum()
    log.info("%s fora da escala (viraram ausente): %d", coluna, depois - antes)
    return df


def faixa_por_corte(df, coluna, cortes, rotulos):
    """Cria uma coluna de faixa a partir de cortes de valor fixos
    (nao por quantil) - usa quando existe um limiar real do dominio,
    nao um recorte estatistico."""
    nova = coluna + "_faixa"
    df[nova] = pd.cut(df[coluna], bins=cortes, labels=rotulos)
    log.info("%s distribuicao:\n%s", nova, df[nova].value_counts(dropna=False).to_string())
    return df


def filtrar_linhas(df, manter):
    """Mantem so as linhas em que 'manter' e verdadeiro (mesmo resultado de
    df[manter].copy()), sem duplicar o DataFrame inteiro na memoria.

    O jeito comum cria uma copia do DataFrame para filtrar e outra no
    .copy(): com um arquivo grande isso estoura a memoria. Aqui, se nao ha
    nada para tirar, devolve o proprio df; senao filtra uma coluna por vez e
    libera a coluna original assim que a nova fica pronta.
    Atencao: quando filtra, esvazia o df recebido; use o retorno.
    """
    if manter.all():
        return df
    colunas = {}
    for coluna in list(df.columns):
        colunas[coluna] = df[coluna][manter]
        del df[coluna]
    return pd.DataFrame(colunas, copy=False)


def ler_csv_por_partes(caminho, linhas_por_parte=100_000, **opcoes):
    """Le um CSV grande sem estourar a memoria, com o MESMO resultado de
    pd.read_csv(caminho, low_memory=False).

    Ler tudo de uma vez obriga o pandas a guardar o arquivo inteiro
    "quebrado em pedacinhos" na memoria, o que pede varios GB a mais que o
    proprio resultado. Juntar as partes com pd.concat tambem duplicaria o
    resultado por um instante. Aqui:

      1a passada: descobre o tipo de cada coluna olhando parte por parte
                  (todas inteiras -> int64; inteiras e decimais ->
                  float64; qualquer texto -> a coluna toda vira texto).
      2a passada: le de novo ja com esses tipos fixos, guardando cada
                  coluna separada (texto repetido fica compartilhado), e
                  monta o resultado coluna por coluna, liberando cada
                  pedaco assim que a coluna fica pronta.

    Os tipos sao decididos para a coluna inteira, e nao parte a parte,
    para que a coluna nao fique com tipos misturados.
    """
    tipos_vistos = {}
    for parte in pd.read_csv(
        caminho, chunksize=linhas_por_parte, low_memory=False, **opcoes
    ):
        for coluna, tipo in parte.dtypes.items():
            tipos_vistos.setdefault(coluna, set()).add(tipo.kind)

    tipos_finais = {}
    for coluna, tipos in tipos_vistos.items():
        if "O" in tipos:
            tipos_finais[coluna] = str
        elif tipos <= {"i", "f"}:
            tipos_finais[coluna] = "float64" if "f" in tipos else "int64"
        else:
            raise ValueError(f"tipo inesperado na coluna {coluna}: {tipos}")

    pedacos = {coluna: [] for coluna in tipos_finais}
    for parte in pd.read_csv(
        caminho,
        chunksize=linhas_por_parte,
        dtype=tipos_finais,
        low_memory=False,
        **opcoes,
    ):
        for coluna in parte.columns:
            if tipos_finais[coluna] is str:
                pedacos[coluna].append(parte[coluna].astype("category"))
            else:
                pedacos[coluna].append(parte[coluna].to_numpy(copy=True))
        del parte

    colunas = {}
    for coluna in list(pedacos):
        lista = pedacos.pop(coluna)
        if tipos_finais[coluna] is str:
            colunas[coluna] = union_categoricals(lista).astype(object)
        else:
            colunas[coluna] = np.concatenate(lista)
        del lista

    df = pd.DataFrame(colunas, copy=False)
    como_texto = sum(1 for t in tipos_finais.values() if t is str)
    log.info(
        "lido em partes de %d linhas: %d colunas (%d como texto)",
        linhas_por_parte, len(tipos_finais), como_texto,
    )
    return df
