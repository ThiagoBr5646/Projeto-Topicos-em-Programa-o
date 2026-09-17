"""Funcoes de limpeza que servem a qualquer fonte.

Aula 6 - Limpeza avancada e engenharia de atributos (ECOX14).

O criterio para uma funcao morar aqui e um so: ela menciona o nome de
alguma fonte? Se menciona (nivel de renda do Banco Mundial, tipo de
treino da academia), fica no script daquela fonte. Se nao menciona,
e generica e mora neste modulo.

O ganho: tirar espaco, padronizar texto e mapear sinonimo estavam
copiados em cada script. Um defeito descoberto obrigava a corrigir em
todos eles, e bastava esquecer um para as fontes passarem a discordar.
Agora uma correcao aqui conserta todas as fontes de uma vez.

Este arquivo nao e executavel: ele e importado pelos scripts de
transformacao. Para o import funcionar, rode sempre a partir da raiz
do projeto (python src/transformar_paises.py) e mantenha os arquivos
em src.
"""

import pandas as pd


def tirar_espacos(df):
    """Remove espacos sobrando dos nomes de coluna e do conteudo texto.

    Defeito tipico das fontes: 'Latin America & Caribbean ' com espaco
    no fim parece igual a 'Latin America & Caribbean', mas para o
    computador sao dois valores diferentes. Dentro de um arquivo so
    isso quase nao incomoda; o custo aparece na juncao com outra fonte,
    quando nenhuma linha casa.
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


def remover_colunas_sem_informacao(df, candidatas=None):
    """Remove colunas que nao distinguem uma linha da outra, contando
    antes de apagar.

    Sao dois casos diferentes, e a funcao separa os dois no relatorio:

    - vazia: nenhum valor preenchido em nenhuma linha;
    - constante: um unico valor repetido em todas as linhas.

    Nos dois casos a coluna nao responde nada, mas apagar continua sendo
    uma decisao. Por isso a funcao devolve o que saiu, para o script
    registrar na proveniencia em vez de apagar em silencio.

    Se `candidatas` for informada, so essas colunas sao avaliadas. Serve
    para proteger colunas constantes que sao metadado proposital (o
    codigo da serie, por exemplo, e constante e precisa ficar).
    """
    colunas = list(df.columns) if candidatas is None else [
        c for c in candidatas if c in df.columns
    ]
    vazias = []
    constantes = {}
    for coluna in colunas:
        serie = df[coluna]
        if str(serie.dtype) in ("object", "string"):
            serie = serie.astype("string").str.strip().replace("", pd.NA)
        preenchidos = int(serie.notna().sum())
        distintos = serie.dropna().unique()
        if preenchidos == 0:
            vazias.append(coluna)
        elif len(distintos) == 1 and preenchidos == len(df):
            constantes[coluna] = distintos[0]

    print("colunas vazias removidas    :", vazias)
    print("colunas constantes removidas:", constantes)
    removidas = vazias + list(constantes)
    return df.drop(columns=removidas), vazias, constantes


def conferir_chave(df, chave, remover=False):
    """Confere se a chave declarada esta mesmo unica.

    Vale para qualquer fonte: a pergunta 'uma linha por o que?' precisa
    de resposta antes de juntar duas tabelas.

    `remover` e explicito de proposito, e vem desligado. Chave ausente
    tambem conta como repetida no pandas (dois ausentes sao 'iguais'),
    e remover sem olhar apaga linha boa so porque a fonte nao preencheu
    o codigo. Por isso a funcao conta os ausentes da chave antes, e
    apagar fica sendo decisao de quem chama.
    """
    return conferir_chave_composta(df, [chave], remover=remover)


def conferir_chave_composta(df, chaves, remover=False):
    """Mesma ideia da anterior, para tabela cuja granularidade precisa
    de mais de uma coluna (por exemplo pais mais ano).

    Devolve (df, repetidas, ausentes_na_chave). Se houver ausente na
    chave, a contagem de repetidas sai tambem sem essas linhas, para
    separar 'a fonte repetiu registro' de 'a fonte nao preencheu o
    codigo'. Sao problemas diferentes e o conserto de cada um e outro.
    """
    ausentes = {c: int(df[c].isna().sum()) for c in chaves}
    repetidas = int(df.duplicated(subset=chaves).sum())

    completas = df.dropna(subset=chaves)
    repetidas_completas = int(completas.duplicated(subset=chaves).sum())

    print("ausentes na chave", chaves, ":", ausentes)
    print("chaves repetidas em", chaves, ":", repetidas,
          "| so entre as linhas com chave completa:", repetidas_completas)
    if repetidas_completas:
        print(completas[completas.duplicated(subset=chaves, keep=False)].head(10))

    if remover:
        antes = len(df)
        df = df.drop_duplicates(subset=chaves)
        print("linhas removidas por chave repetida:", antes - len(df))
    return df, repetidas_completas, ausentes


def ano_para_inteiro(serie):
    """Converte uma coluna de ano para inteiro, nao para data.

    Um ano nao tem mes, nao tem dia, nao tem hora e nao tem fuso.
    Converter '2023' para 2023-01-01 00:00:00 nao acrescenta
    informacao: acrescenta precisao falsa, um dia e uma hora que
    ninguem mediu. Para serie anual, inteiro e o tipo honesto - ordena,
    subtrai e compara sem inventar nada.

    Int64 com I maiusculo e o inteiro do pandas que aceita ausente.
    """
    return pd.to_numeric(serie, errors="coerce").astype("Int64")
