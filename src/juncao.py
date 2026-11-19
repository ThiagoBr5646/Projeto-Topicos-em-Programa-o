"""Funcoes de juncao que servem a qualquer par de tabelas.

Aula 7 - Enriquecimento: juntar fontes (ECOX14).

Mesmo criterio do limpeza.py: nenhuma funcao aqui menciona o nome de
uma fonte. O que e especifico de cada juncao (quais tabelas, qual
coluna, qual dicionario de mapeamento) fica no script que junta.

As quatro perguntas da aula, nesta ordem:
    1. Quais duas tabelas? E qual e o grao de cada uma?
    2. Por qual coluna? A chave esta limpa dos dois lados?
    3. O que fazer com quem nao casa? (o tipo de juncao decide)
    4. Como sei que deu certo? (a contagem antes e depois precisa fechar)

Este arquivo nao e executavel: ele e importado.

Aula 8: os print viraram log. Este modulo fica embaixo na hierarquia:
nao importa config nem nenhuma etapa, so pede um logger com o proprio
nome. Quem decide se a mensagem aparece, e onde, e quem roda.
"""
from pathlib import Path
import logging

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)


def conferir_chave(df, coluna):
    """Confere se a coluna serve de chave do cadastro: ausentes e repetidos.

    E o lado da direita que precisa ter chave unica. Se a chave repete
    no cadastro, cada linha da esquerda casa com mais de uma e a tabela
    incha sem avisar - o grao muda.
    """
    ausentes = int(df[coluna].isna().sum())
    repetidos = int(df[coluna].dropna().duplicated().sum())
    log.info("chave %s: %d linhas | ausentes = %d | repetidos = %d",
             coluna, len(df), ausentes, repetidos)
    if repetidos:
        log.warning("chave %s repete %d vezes: a juncao vai inflar a tabela",
                    coluna, repetidos)
    return ausentes, repetidos


def comparar_chaves(esquerda, chave_esq, direita, chave_dir):
    """PASSO 1: confere as chaves ANTES de juntar.

    Os tres numeros (so na esquerda, so na direita, nos dois) sao a
    previsao do que a juncao vai fazer: anotados antes, comparados
    depois. Confere tambem o tipo, porque '02000' (texto) e 2000
    (numero) nunca casam, e a juncao nao avisa - so devolve ausente.
    """
    tipo_esq = str(esquerda[chave_esq].dtype)
    tipo_dir = str(direita[chave_dir].dtype)
    log.debug("tipo da chave: esquerda = %s | direita = %s", tipo_esq, tipo_dir)
    if tipo_esq != tipo_dir:
        log.warning("tipos de chave diferentes (%s x %s): converta antes de "
                    "juntar", tipo_esq, tipo_dir)

    esq = set(esquerda[chave_esq].dropna())
    dir_ = set(direita[chave_dir].dropna())
    sem_chave = int(esquerda[chave_esq].isna().sum())

    previsao = {
        "so_na_esquerda": sorted(esq - dir_),
        "so_na_direita": sorted(dir_ - esq),
        "nos_dois": sorted(esq & dir_),
        "linhas_esquerda_sem_chave": sem_chave,
    }
    log.info("previsao: so na esquerda = %d | so na direita = %d | "
             "nos dois = %d | linhas da esquerda sem chave = %d",
             len(previsao["so_na_esquerda"]), len(previsao["so_na_direita"]),
             len(previsao["nos_dois"]), sem_chave)
    return previsao


def juntar(esquerda, direita, chave_esq, chave_dir):
    """PASSO 2: a juncao, com left e validate.

    how='left': nenhuma linha da esquerda some. Quem nao casa fica na
    tabela com ausente nas colunas da direita - visivel. O inner apagaria
    essas linhas em silencio, e o problema sumiria junto.

    validate='many_to_one': declara a expectativa - muitas linhas da
    esquerda para UMA linha da direita. Se a chave repetir na direita,
    o pandas levanta erro em vez de devolver uma tabela inflada.

    As chaves podem ter nomes diferentes: o que precisa ser igual e o
    conteudo, nao o nome da coluna.
    """
    return esquerda.merge(
        direita,
        left_on=chave_esq,
        right_on=chave_dir,
        how="left",
        validate="many_to_one",
    )


def validar(esquerda, resultado, chave_dir):
    """PASSO 3: valida antes de comemorar.

    Tres conferencias que pegam a maior parte dos erros de juncao:
      - resultado com MENOS linhas: usou inner e perdeu quem nao casou;
      - resultado com MAIS linhas: a chave repete na direita, o grao mudou;
      - MESMO numero: a chave e unica na direita, como esperado.

    Devolve justamente as linhas que nao casaram: e esse pedaco que se
    investiga e se descreve no README.
    """
    antes = len(esquerda)
    depois = len(resultado)
    sem_par = resultado[chave_dir].isna()
    log.info("esquerda: %d | resultado: %d | sem par: %d",
             antes, depois, int(sem_par.sum()))
    if depois != antes:
        log.warning("o numero de linhas mudou na juncao: %d -> %d",
                    antes, depois)
    if sem_par.any():
        log.warning("%d linhas sem par na juncao", int(sem_par.sum()))
    return resultado[sem_par]
