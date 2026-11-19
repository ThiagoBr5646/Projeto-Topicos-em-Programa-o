"""Enriquece a prata da academia com o Compendio de Atividades Fisicas.

Aula 7 - Enriquecimento: juntar fontes (ECOX14).

Enriquecer e acrescentar a um registro uma informacao que ja existe em
outro lugar, usando algo que os dois tem em comum. Nada e inventado: o
MET de cada tipo de treino ja existia, separado, no Compendio. A camada
continua sendo a Prata - sai mais uma tabela tratada, so que com
informacao de duas fontes.

O problema que ficou em aberto (README, "Defeitos conhecidos da fonte"):
as calorias por hora da base sao praticamente iguais entre tipos de
treino - HIIT e yoga com 717 kcal/h. Dentro da base nao havia como
saber se isso estava errado, porque nenhuma coluna diz quanto cada tipo
de treino costuma gastar. Essa informacao esta na outra tabela.

As quatro perguntas da aula, respondidas para esta juncao:

1. Quais duas tabelas, e qual o grao de cada uma?
   esquerda : gym_members.parquet - uma linha = uma sessao de um praticante
   direita  : compendio.parquet   - uma linha = uma atividade do Compendio
   resultado: uma linha = uma sessao. O grao NAO muda, porque cada
              sessao casa com no maximo uma atividade (many_to_one).

2. Por qual coluna?
   codigo_compendio (academia) = codigo (Compendio). A academia nao tem
   codigo: ele sai do dicionario MAPA_TREINO_COMPENDIO, que traduz o tipo
   de treino para o codigo da atividade - motivo "grafia diferente" da
   aula: 'Strength' e 'Resistance (weight) training' sao a mesma coisa
   escrita de jeitos diferentes. Os dois lados ficam como texto, porque
   o codigo tem zero a esquerda.

3. O que fazer com quem nao casa?
   how='left': a sessao sem par continua na tabela, com MET ausente, e
   aparece na validacao. Nada some em silencio.

4. Como sei que deu certo?
   sessoes antes = sessoes depois, e a contagem de sem par e conferida
   contra a previsao do passo 1.

Aula 8: caminhos vieram do config.py; print virou log. O MAPA de
treino continua aqui: e decisao especifica desta juncao, nao parametro.

Como executar, de qualquer pasta (depois das duas transformacoes):
    python src/pipeline.py enriquecimento   (esta etapa e as seguintes)
    python src/enriquecer_gym_members.py    (so este script)
"""
from datetime import datetime
import json
from pathlib import Path
import logging

import pandas as pd

import juncao  # modulo do projeto, em src/
from config import (PRATA, PRATA_ACADEMIA as ACADEMIA,
                    PRATA_COMPENDIO as COMPENDIO,
                    PRATA_ENRIQUECIDA as DESTINO, PROVENIENCIA_PRATA)

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)

PESO = "Weight (kg)"
DURACAO = "Session_Duration (hours)"
CALORIAS = "Calories_Burned"

# Dicionario de mapeamento: tipo de treino da academia (treino_chave,
# ja sem acento e em minuscula) -> codigo do Compendio. Uma linha por
# tipo, escrita a mao, porque escolher a atividade equivalente exige
# conhecer o assunto.
#
# Criterio, o mesmo para os quatro: a base nao informa o esforco da
# sessao, entao fica a descricao mais geral do tipo; quando o Compendio
# so separa por esforco, fica "moderate effort". Escolher "vigorous"
# seria inventar uma intensidade que a fonte nao registrou.
MAPA_TREINO_COMPENDIO = {
    "cardio": "02000",    # Aerobic, general -> 7.3 MET
    "hiit": "02210",      # High intensity interval exercise, moderate effort -> 7.0
    "strength": "02054",  # Resistance (weight) training, multiple exercises,
                          # 8-15 reps at varied resistance -> 3.5
    "yoga": "02175",      # Yoga, General -> 2.3
}

# Reduzir antes de juntar: do cadastro, so o que a pergunta usa.
COLUNAS_DO_CADASTRO = ["codigo", "met", "atividade_compendio", "met_estimado"]


def carregar():
    """Le as duas pratas: a academia e o cadastro do Compendio."""
    academia = pd.read_parquet(ACADEMIA)
    compendio = pd.read_parquet(COMPENDIO)
    log.info("academia : %s %s", ACADEMIA.name, academia.shape)
    log.info("compendio: %s %s", COMPENDIO.name, compendio.shape)
    return academia, compendio


def responder_grao(academia, compendio):
    """Antes de qualquer juncao, responder em voz alta: o que e uma linha
    em cada tabela, e o que vai ser uma linha no resultado."""
    log.debug("uma linha na esquerda : uma sessao de um praticante "
              "(%d sessoes)", len(academia))
    log.debug("uma linha na direita  : uma atividade do Compendio "
              "(%d atividades)", len(compendio))
    log.debug("uma linha no resultado: uma sessao (o grao nao deve mudar)")


def traduzir_treino(academia):
    """Cria a chave da esquerda: o codigo do Compendio de cada sessao.

    Tipo de treino fora do dicionario vira ausente - e vai aparecer
    como 'sem par' na validacao, em vez de sumir.
    """
    academia["codigo_compendio"] = (
        academia["treino_chave"].map(MAPA_TREINO_COMPENDIO).astype("string"))
    sem_codigo = academia.loc[academia["codigo_compendio"].isna(), "Workout_Type"]
    if len(sem_codigo):
        log.warning("tipos de treino sem codigo no dicionario: %s",
                    sorted(sem_codigo.astype(str).unique()))
    return academia


def comparar_por_treino(resultado):
    """PASSO 4: o problema em aberto se fecha.

    Agora a coluna met existe nesta tabela, e da para comparar o que a
    base diz com o que o Compendio espera, tipo de treino a tipo de
    treino. kcal/h esperada = MET x peso (1 MET ~ 1 kcal/kg/h).
    """
    tabela = (
        resultado.assign(kcal_h_compendio=resultado["met"] * resultado[PESO])
        .groupby("Workout_Type", observed=True)
        .agg(
            sessoes=("met", "size"),
            met=("met", "first"),
            kcal_h_base=("calorias_por_hora", "mean"),
            kcal_h_compendio=("kcal_h_compendio", "mean"),
        )
        .round(1)
    )
    tabela["base_sobre_compendio"] = (
        tabela["kcal_h_base"] / tabela["kcal_h_compendio"]).round(2)
    log.info("kcal/h base / kcal/h Compendio por treino: %s",
             tabela["base_sobre_compendio"].to_dict())
    log.debug("\n%s", tabela.to_string())
    return tabela


def calorias_met(df):
    """PASSO 5: ATRIBUTO que so existe depois da juncao.

    calorias_met = MET x peso (kg) x duracao (h), em kcal: a estimativa
    do Compendio para a mesma sessao. Antes da juncao nao dava para
    calcular, porque o MET estava na outra tabela.

    Serve a pergunta norteadora porque usa duas caracteristicas do
    praticante - o peso e o tipo de treino - que o Compendio diz pesarem
    no gasto e que a formula da base ignora; colocar as duas estimativas
    lado a lado mostra quanto da resposta da base vem do gerador dos
    dados, e nao da fisiologia.

    razao_base_met = Calories_Burned / calorias_met: quantas vezes a base
    da o que o Compendio espera. 1 seria concordancia.
    """
    df["calorias_met"] = (df["met"] * df[PESO] * df[DURACAO]).round(1)
    df["razao_base_met"] = (df[CALORIAS] / df["calorias_met"]).round(2)

    log.debug("calorias_met: %s", df["calorias_met"].describe().round(1).to_dict())
    log.debug("razao_base_met: %s",
              df["razao_base_met"].describe().round(2).to_dict())

    # Quanto cada coluna explica das calorias da base (R2 de uma reta).
    r2_duracao = df[CALORIAS].corr(df[DURACAO]) ** 2
    r2_met = df[CALORIAS].corr(df["calorias_met"]) ** 2
    log.info("R2 calorias da base x duracao: %.1f%% | x calorias_met: %.1f%%",
             100 * r2_duracao, 100 * r2_met)
    return df, round(r2_duracao, 3), round(r2_met, 3)


def salvar(df):
    """Grava a prata enriquecida. Mesmo grao da academia: uma sessao por
    linha, agora com o MET e a estimativa do Compendio ao lado."""
    PRATA.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DESTINO, index=False)
    log.info("salvo: %s %s", DESTINO.name, df.shape)
    return DESTINO


def registrar(destino, previsao, antes, depois, sem_par, tabela,
              r2_duracao, r2_met):
    """Registra a proveniencia: uma linha por execucao, com os numeros
    reais desta execucao (nao fixos no texto)."""
    info = {
        "origem": [ACADEMIA.name, COMPENDIO.name],
        "arquivo_prata": destino.name,
        "juncao": "codigo_compendio = codigo, how=left, validate=many_to_one",
        "mapa_treino_compendio": MAPA_TREINO_COMPENDIO,
        "previsao_passo_1": {
            "so_na_academia": previsao["so_na_esquerda"],
            "so_no_compendio": len(previsao["so_na_direita"]),
            "nos_dois": previsao["nos_dois"],
            "sessoes_sem_codigo": previsao["linhas_esquerda_sem_chave"],
        },
        "linhas_antes": antes,
        "linhas_depois": depois,
        "sem_par": sem_par,
        "por_treino": tabela.reset_index().astype({"Workout_Type": str})
                            .to_dict(orient="records"),
        "r2_calorias_x_duracao": r2_duracao,
        "r2_calorias_x_calorias_met": r2_met,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    with PROVENIENCIA_PRATA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    return info


def main():
    academia, compendio = carregar()
    responder_grao(academia, compendio)
    academia = traduzir_treino(academia)
    cadastro = compendio[COLUNAS_DO_CADASTRO]

    log.info("passo 1: conferir as chaves antes de juntar")
    juncao.conferir_chave(cadastro, "codigo")
    previsao = juncao.comparar_chaves(
        academia, "codigo_compendio", cadastro, "codigo")

    log.info("passo 2: juntar (left, many_to_one)")
    resultado = juncao.juntar(academia, cadastro, "codigo_compendio", "codigo")

    log.info("passo 3: validar antes de comemorar")
    sem_par = juncao.validar(academia, resultado, "codigo")
    if len(sem_par):
        log.warning("sem par por tipo de treino: %s",
                    sem_par["Workout_Type"].value_counts().to_dict())

    log.info("passo 4: o problema em aberto se fecha")
    tabela = comparar_por_treino(resultado)

    log.info("passo 5: atributo que so existe depois da juncao")
    resultado, r2_duracao, r2_met = calorias_met(resultado)

    destino = salvar(resultado)
    info = registrar(destino, previsao, len(academia), len(resultado),
                     len(sem_par), tabela, r2_duracao, r2_met)
    return info


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()
