"""Funcoes de limpeza que servem a qualquer fonte.

Aula 6 - Limpeza avancada e engenharia de atributos (ECOX14).

O criterio para uma funcao morar aqui e um so: ela menciona o nome da
fonte? Se menciona (o tipo de treino da academia, por exemplo), fica no
script da fonte. Se nao menciona, e generica e mora neste modulo.

O ganho: tirar espaco, padronizar texto e mapear sinonimo sao tarefas
que toda base precisa. Escritas uma vez aqui, servem para qualquer base
que entrar no projeto, e uma correcao feita aqui vale para todas.

Este arquivo nao e executavel: ele e importado pelos scripts de
transformacao, que ficam todos em src.

Aula 8: este modulo esta embaixo na hierarquia de imports. Ele nao
importa config nem nenhuma etapa - e por isso da para usar (e testar)
as funcoes daqui sem rodar o pipeline inteiro.
"""

import pandas as pd


def tirar_espacos(df):
    """Remove espacos sobrando dos nomes de coluna e do conteudo texto.

    Defeito tipico das fontes: 'Yoga ' com espaco no fim parece igual a
    'Yoga', mas para o computador sao dois valores diferentes, e o
    agrupamento por tipo de treino passa a mostrar dois grupos. Dentro
    de um arquivo so isso ja atrapalha; o custo maior aparece na juncao
    com outra fonte, quando nenhuma linha casa.
    """
    df.columns = df.columns.str.strip()
    for coluna in df.select_dtypes(include=["object", "string"]):
        df[coluna] = df[coluna].str.strip()
    return df


def chave_texto(serie):
    """Versao comparavel de um texto: sem acento, sem espaco sobrando
    e tudo em minuscula.

    Repare no nome: chave_texto, nao limpar_texto. O resultado serve
    para comparar, agrupar e juntar, nao para exibir. O rotulo original
    continua na tabela, porque quem some com o acento na hora de exibir
    esta jogando fora informacao.
    """
    s = serie.astype("string").str.strip().str.lower()
    s = s.str.normalize("NFKD")
    s = s.str.encode("ascii", errors="ignore")
    return s.str.decode("utf-8")


def aplicar_mapa(serie, mapa):
    """Troca variantes pelo valor canonico.

    O que nao estiver no mapa fica como esta. A funcao e generica e
    mora aqui; o dicionario e especifico de cada fonte e mora no script
    dela, escrito de forma explicita, porque mapear sinonimo exige
    conhecer o assunto.
    """
    return serie.replace(mapa)
