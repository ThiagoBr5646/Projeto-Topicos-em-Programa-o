"""Configuracao do projeto: caminhos, parametros e o log.

Aula 8 - De scripts soltos a pipeline (ECOX14).

O teste para uma linha morar aqui: se alguem for rodar o projeto em
outra maquina, ou com outra extracao, quais linhas essa pessoa precisa
editar? Essas linhas pertencem ao config.

O que entra: caminhos de pasta e arquivo, identificacao das fontes,
faixas de plausibilidade que se ajustam e reexecutam.
O que NAO entra: logica de transformacao, nada que mude a cada
execucao e nenhum segredo. O token do Kaggle fica no kaggle.json, que
esta no .gitignore - este arquivo vai para o GitHub.

Regra de dependencia: config nao importa nenhum modulo do projeto.
Todo mundo pode importar o config; o config nao conhece ninguem.
"""
from pathlib import Path
import logging

# ---- Caminhos -------------------------------------------------------
# RAIZ calculada a partir deste arquivo (src/config.py -> raiz). O
# caminho deixa de depender da pasta de onde o comando foi rodado.
RAIZ = Path(__file__).resolve().parent.parent

DADOS = RAIZ / "dados"
BRONZE = DADOS / "bronze"
PRATA = DADOS / "prata"
OURO = DADOS / "ouro"

# Aula 9: a camada Ouro deixa de ser pasta e vira esquema dentro do banco.
BANCO = OURO / "projeto.duckdb"

# Aula 10: o projeto dbt que constroi a Ouro.
DBT = RAIZ / "ecox14"

RELATORIOS = RAIZ / "relatorios"
LOG = RAIZ / "pipeline.log"

# ---- Fonte 1: academia (Kaggle) --------------------------------------
DATASET_KAGGLE = "valakhorasani/gym-members-exercise-dataset"
BRONZE_ACADEMIA = BRONZE / "gym_members"
PADRAO_ACADEMIA = "gym_members_exercise_tracking_*.csv"
PRATA_ACADEMIA = PRATA / "gym_members.parquet"

# ---- Fonte 2: Compendio de Atividades Fisicas (CSV copiado a mao) ----
BRONZE_COMPENDIO = BRONZE / "compendio"
PADRAO_COMPENDIO = "compendio_condicionamento_*.csv"
PRATA_COMPENDIO = PRATA / "compendio.parquet"

# ---- Resultado da juncao (aula 7) ------------------------------------
PRATA_ENRIQUECIDA = PRATA / "gym_members_enriquecida.parquet"
PROVENIENCIA_PRATA = PRATA / "proveniencia.jsonl"

# ---- Parametros que se ajustam e reexecutam --------------------------
# kcal/h plausivel para treino de adulto (aula 6). Fora disso: sinaliza.
FAIXA_CALORIAS_HORA = (200, 1500)
# MET plausivel: do repouso sentado (~1) ao esforco maximo (~23).
FAIXA_MET = (0.9, 25.0)


def configurar_log(nivel=logging.INFO):
    """Liga o log do projeto: na tela e no arquivo pipeline.log.

    Os dois handlers fazem a mensagem sair na tela e ir para o arquivo
    ao mesmo tempo. O arquivo esta no .gitignore. Chamar duas vezes nao
    duplica as linhas (force=True troca a configuracao anterior).

    A data entra no carimbo junto com a hora: o arquivo acumula varias
    execucoes, e "o que aconteceu ontem as tres da tarde" so tem
    resposta se o dia estiver escrito.
    """
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
