"""Transforma a Bronze da academia (Kaggle) na camada Prata.

Aula 6 - Limpeza avancada e engenharia de atributos (ECOX14).
Este e o PASSO 10: o atributo derivado escolhido por mim, o que serve a
pergunta norteadora do projeto.

Pergunta norteadora (primeira entrega):
    Quais caracteristicas do praticante mais explicam as calorias
    queimadas por sessao?

Atributo derivado: calorias_por_hora.
    Uma frase, que e o criterio da aula: dividir as calorias pela
    duracao separa "treinou muito tempo" de "treinou forte", e e isso
    que a pergunta quer saber - sem dividir, quem fica duas horas em
    ritmo leve aparece como quem gasta mais.
    Nao repete coluna existente: Calories_Burned e
    'Session_Duration (hours)' estao na fonte, a razao entre as duas
    nao. E nao e o caso do BMI, que a fonte JA publica derivado de peso
    e altura - refazer o BMI seria criar coluna que so ocupa espaco e
    que um dia discorda da original.

Aula 8: caminhos vieram do config.py e os print viraram log.
Aula 9: a prata ganhou sessao_id, a chave que a camada Ouro precisa
(a fonte nao traz identificador nenhum).

Como executar, de qualquer pasta:
    python src/pipeline.py transformacao   (esta etapa e as seguintes)
    python src/transformar_gym_members.py  (so este script)
"""
from datetime import datetime
import json
from pathlib import Path
import logging

import pandas as pd

import limpeza  # modulo do projeto, em src/
from config import (BRONZE_ACADEMIA, FAIXA_CALORIAS_HORA, PADRAO_ACADEMIA,
                    PRATA, PRATA_ACADEMIA, PROVENIENCIA_PRATA)

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)

DURACAO = "Session_Duration (hours)"
CALORIAS = "Calories_Burned"

# Nivel de experiencia vem como 1, 2 e 3: e numero, mas nao se soma.
# E categoria COM ordem, e declarar a ordem faz comparar funcionar.
ORDEM_EXPERIENCIA = ["iniciante", "intermediario", "avancado"]
ROTULO_EXPERIENCIA = {1: "iniciante", 2: "intermediario", 3: "avancado"}

# Categorias sem ordem desta fonte: nenhuma delas tem escala natural.
CATEGORIAS_SEM_ORDEM = ["Gender", "Workout_Type"]

# Dicionario de sinonimos desta fonte. A base do Kaggle vem
# padronizada, e por isso o mapa esta vazio: escrever variante que a
# fonte nao tem seria inventar defeito. Ele fica declarado para quando
# aparecer 'hiit', 'HIIT ' ou 'High Intensity' em uma extracao futura.
MAPA_TREINO = {}


def carregar():
    """Le o arquivo mais recente da bronze (a data no nome ordena)."""
    arquivos = sorted(BRONZE_ACADEMIA.glob(PADRAO_ACADEMIA))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE_ACADEMIA}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    log.info("lido: %s %s", caminho.name, df.shape)
    return df, caminho


def olhar_antes_de_decidir(df):
    """Mostra colunas e ausentes antes de qualquer alteracao."""
    log.debug("colunas: %s", df.columns.tolist())
    ausentes = int(df.isna().sum().sum())
    log.info("valores ausentes na bronze: %d", ausentes)
    if ausentes:
        log.warning("ausentes por coluna: %s",
                    {c: n for c, n in df.isna().sum().items() if n})


def tipar_categorias(df):
    """Da tipo as colunas categoricas: sem ordem as duas primeiras, com
    ordem o nivel de experiencia.

    Guardadas como texto livre, nada impede um 'Yogaa' de entrar. Como
    categoria, o valor fora da lista vira ausente, e o codigo passa a
    dizer em voz alta o que estava escondido no meio do texto.
    """
    df["treino_chave"] = limpeza.aplicar_mapa(
        limpeza.chave_texto(df["Workout_Type"]), MAPA_TREINO)

    for coluna in CATEGORIAS_SEM_ORDEM:
        df[coluna] = pd.Categorical(df[coluna])
        log.debug("%s -> %s", coluna, list(df[coluna].cat.categories))

    df["experiencia"] = pd.Categorical(
        df["Experience_Level"].map(ROTULO_EXPERIENCIA),
        categories=ORDEM_EXPERIENCIA,
        ordered=True,
    )
    fora_da_escala = int(df["experiencia"].isna().sum())
    if fora_da_escala:
        log.warning("experiencia fora da escala 1-3: %d", fora_da_escala)
    return df, fora_da_escala


def calorias_por_hora(df, calorias=CALORIAS, duracao=DURACAO):
    """Cria o atributo derivado: intensidade da sessao, em kcal/h.

    Divide para tirar o efeito do tamanho, que e a familia 'razao ou
    taxa' da aula. A duracao zero viraria divisao por quase nada e
    devolveria valor absurdo (a aula avisa: variacao de 4000% costuma
    ser divisao por valor quase zero), por isso ela vira ausente antes
    da conta, e a contagem fica registrada.
    """
    horas = df[duracao].where(df[duracao] > 0)
    sem_duracao = int(horas.isna().sum())

    df["calorias_por_hora"] = (df[calorias] / horas).round(1)

    if sem_duracao:
        log.warning("sessoes com duracao invalida (viraram ausentes): %d",
                    sem_duracao)
    log.debug("calorias_por_hora: %s",
              df["calorias_por_hora"].describe().round(1).to_dict())
    return df, sem_duracao


def conferir_plausibilidade(df):
    """Confere se o atributo novo tem valor plausivel.

    Nao e teste automatizado, e conferencia antes de commitar: kcal/h
    de treino de gente adulta cai, grosso modo, entre 200 e 1500. O que
    passar disso nao e removido, e sinalizado - remover exige dono.
    """
    faixa = FAIXA_CALORIAS_HORA
    fora = df["calorias_por_hora"].notna() & ~df["calorias_por_hora"].between(*faixa)
    if fora.any():
        log.warning("calorias_por_hora fora de %s: %d sessoes", faixa,
                    int(fora.sum()))
        log.debug("\n%s", df.loc[fora, [CALORIAS, DURACAO,
                                        "calorias_por_hora"]].head())
    return int(fora.sum())


def numerar_sessoes(df):
    """Cria sessao_id: o numero da sessao, de 1 a n, na ordem da bronze.

    Aula 9. A camada Ouro precisa de uma chave para a tabela fato, e a
    fonte nao traz identificador nenhum - nem de sessao, nem de
    praticante. O numero nasce aqui, na prata, e nao na Ouro, porque
    precisa atravessar a juncao da aula 7 junto com a linha.

    Vale dentro de uma extracao: a mesma bronze gera sempre os mesmos
    numeros. Uma extracao nova, com as linhas em outra ordem, numera de
    outro jeito - por isso o numero nao deve ser guardado fora do projeto.
    """
    df = df.reset_index(drop=True)
    df.insert(0, "sessao_id", pd.RangeIndex(1, len(df) + 1))
    return df


def salvar(df):
    """Grava a prata em Parquet, sem data no nome: a prata e
    reconstruivel, cada execucao substitui a versao anterior."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA_ACADEMIA
    df.to_parquet(destino, index=False)
    log.info("salvo: %s %s", destino.name, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    """Registra a proveniencia: uma linha por execucao, no fim do arquivo."""
    info = {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    with PROVENIENCIA_PRATA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    return info


def main():
    df, origem = carregar()
    antes = len(df)
    olhar_antes_de_decidir(df)

    df = limpeza.tirar_espacos(df)
    repetidas = int(df.duplicated().sum())
    if repetidas:
        log.warning("linhas identicas repetidas removidas: %d", repetidas)
    df = df.drop_duplicates()
    df = numerar_sessoes(df)

    df, experiencia_fora = tipar_categorias(df)
    df, sem_duracao = calorias_por_hora(df)
    fora_da_faixa = conferir_plausibilidade(df)

    depois = len(df)
    destino = salvar(df)

    decisoes = [
        "Espacos removidos de nomes de coluna e de texto "
        "(src/limpeza.tirar_espacos).",
        f"Linhas identicas repetidas removidas: {repetidas}.",
        "Gender e Workout_Type tipadas como categoria sem ordem; "
        "treino_chave criada ao lado (sem acento, minuscula) para comparar "
        "e juntar, mantendo o rotulo original para exibir.",
        "Experience_Level (1, 2, 3) virou a categoria ordenada "
        f"experiencia (iniciante < intermediario < avancado); fora da "
        f"escala: {experiencia_fora}. O numero original ficou na tabela.",
        "ATRIBUTO DERIVADO calorias_por_hora = Calories_Burned / "
        "Session_Duration (hours). Serve a pergunta norteadora: separa "
        "intensidade de duracao, e sem ele quem treina mais tempo em "
        "ritmo leve aparece como quem gasta mais. Sessoes com duracao "
        f"invalida viraram ausentes: {sem_duracao}.",
        f"Conferencia de plausibilidade de calorias_por_hora "
        f"({FAIXA_CALORIAS_HORA[0]} a {FAIXA_CALORIAS_HORA[1]} kcal/h): "
        f"{fora_da_faixa} fora da faixa, sinalizadas e nao removidas.",
        "sessao_id = numero da sessao (1 a n) na ordem da bronze, depois "
        "de remover as repetidas. A fonte nao tem identificador; a chave "
        "e a que a tabela fato da Ouro usa (aula 9).",
        "PENDENTE desta fonte: as checagens de qualidade da aula 5 "
        "(valor extremo por IQR e z-score, faixa valida por dominio) "
        "ainda nao foram feitas nesta base; esta prata cobre a limpeza "
        "e o atributo derivado da aula 6.",
    ]
    info = registrar(origem, destino, antes, depois, decisoes)

    log.info("academia: %d linhas na bronze -> %d na prata", antes, depois)
    return info


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()
