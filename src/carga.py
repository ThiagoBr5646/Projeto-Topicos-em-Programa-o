"""Carga: coloca a Prata dentro do DuckDB e (ate a aula 10) construia a Ouro.

Aula 9 - Modelagem e carga em banco (ECOX14).
Aula 10 - construir_ouro() saiu do main: quem constroi a Ouro agora e o
          dbt (pasta ecox14/). A funcao ficou no arquivo, comentada no
          main, para comparar as duas formas.
Aula 11 - conferir() tambem saiu do main: as conferencias viraram
          testes do dbt, que falham sozinhos e param o pipeline.

O que continua em Python, porque nao e transformacao: abrir o banco,
criar os esquemas e ler os Parquet da Prata para dentro dele.

Camada deixa de ser pasta e vira esquema:
    dados/ouro/projeto.duckdb
        prata.gym_members               (entra como esta)
        prata.compendio                 (entra como esta)
        prata.gym_members_enriquecida   (entra como esta)
        ouro.dim_treino                 (nasce aqui dentro, em SQL)
        ouro.dim_praticante
        ouro.fato_sessao
        ouro.vw_sessao_completa         (view)

Como executar, de qualquer pasta:
    python src/pipeline.py carga    (carga e modelagem)
    python src/carga.py             (so a carga)
"""
from pathlib import Path
import logging

import duckdb

from config import (BANCO, OURO, PRATA_ACADEMIA, PRATA_COMPENDIO,
                    PRATA_ENRIQUECIDA)

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)

# Nome da tabela no esquema prata -> arquivo Parquet da prata.
TABELAS_PRATA = {
    "gym_members": PRATA_ACADEMIA,
    "compendio": PRATA_COMPENDIO,
    "gym_members_enriquecida": PRATA_ENRIQUECIDA,
}


def conectar():
    """Abre o banco. connect cria o arquivo se ele nao existir: nao ha
    servidor, senha nem porta. Apagar o arquivo e recomecar do zero."""
    OURO.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(BANCO))


def criar_esquemas(con):
    """Uma camada, um esquema: prata (entra pronta) e ouro (nasce aqui)."""
    con.execute("CREATE SCHEMA IF NOT EXISTS prata")
    con.execute("CREATE SCHEMA IF NOT EXISTS ouro")


def um_valor(con, sql):
    """Le um numero de dentro do banco (con.execute, nao con.sql).

    fetchall, e nao fetchone: a partir do DuckDB 2.0 um resultado lido
    pela metade deixa a conexao ocupada, e o proximo comando falha com
    'connection has an unfinished result'. A consulta devolve uma linha
    so, entao ler tudo custa o mesmo.
    """
    return con.execute(sql).fetchall()[0][0]


def carregar_prata(con):
    """Le os Parquet da prata direto, sem etapa de importacao.

    O Parquet guarda o tipo de cada coluna (decisao da aula 5): o codigo
    do Compendio chega como texto, com o zero a esquerda, sem precisar
    declarar nada. as_posix() troca a barra invertida do Windows pela
    barra comum, que e o que o SQL espera dentro de uma string.
    """
    for tabela, arquivo in TABELAS_PRATA.items():
        if not arquivo.exists():
            raise FileNotFoundError(
                f"{arquivo.name} nao existe: rode antes as etapas "
                "transformacao e enriquecimento")
        caminho = arquivo.as_posix()
        con.execute(f"""
            CREATE OR REPLACE TABLE prata.{tabela} AS
            SELECT * FROM read_parquet('{caminho}')
        """)
        linhas = um_valor(con, f"SELECT COUNT(*) FROM prata.{tabela}")
        log.info("prata.%s: %d registros", tabela, linhas)


# ---------------------------------------------------------------------
# Aula 9: a Ouro escrita em SQL dentro do Python. Desde a aula 10 quem
# faz isto e o dbt (ecox14/models). Fica aqui para comparar.
# ---------------------------------------------------------------------
def construir_ouro(con):
    """Esquema estrela: uma fato no meio, duas dimensoes em volta.

    Grao da fato: uma linha de fato_sessao e uma sessao de treino de um
    praticante. Os AS trocam os nomes da fonte (em ingles, com espaco e
    parentese) por nomes que uma pessoa entende: a Ouro e a camada que
    vai ser consultada por gente.
    """
    # Dimensao 1: o tipo de treino, com o que o Compendio diz dele.
    # O filtro codigo IS NOT NULL deixa de fora o treino que nao achou
    # par no Compendio na aula 7 (hoje: nenhum).
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_treino AS
        SELECT DISTINCT
            treino_chave        AS treino_id,
            Workout_Type        AS tipo_treino,
            codigo              AS codigo_compendio,
            atividade_compendio,
            met,
            met_estimado
        FROM prata.gym_members_enriquecida
        WHERE codigo IS NOT NULL
    """)

    # Dimensao 2: quem treinou. A fonte registra uma sessao por
    # praticante e nao tem identificador de pessoa: o praticante herda o
    # numero da sessao.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_praticante AS
        SELECT
            sessao_id                         AS praticante_id,
            Gender                            AS genero,
            Age                               AS idade,
            "Weight (kg)"                     AS peso_kg,
            "Height (m)"                      AS altura_m,
            BMI                               AS imc,
            Fat_Percentage                    AS gordura_pct,
            Resting_BPM                       AS bpm_repouso,
            "Water_Intake (liters)"           AS agua_litros,
            "Workout_Frequency (days/week)"   AS treinos_por_semana,
            Experience_Level                  AS nivel_experiencia,
            experiencia
        FROM prata.gym_members_enriquecida
    """)

    # Fato: os numeros da sessao. O WHERE e o mesmo filtro de
    # integridade da dim_treino: a validacao do join da aula 7 virou,
    # aqui, a garantia de que nenhuma sessao aponta para treino ausente.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_sessao AS
        SELECT
            sessao_id,
            sessao_id                    AS praticante_id,
            treino_chave                 AS treino_id,
            "Session_Duration (hours)"   AS duracao_h,
            Calories_Burned              AS calorias_base,
            Avg_BPM                      AS bpm_medio,
            Max_BPM                      AS bpm_max,
            calorias_por_hora,
            calorias_met,
            razao_base_met
        FROM prata.gym_members_enriquecida
        WHERE codigo IS NOT NULL
    """)

    # A tabela achatada da aula 7 volta como consulta salva: nao guarda
    # dado, roda o join na hora e nunca fica desatualizada.
    con.execute("""
        CREATE OR REPLACE VIEW ouro.vw_sessao_completa AS
        SELECT f.*,
               p.genero, p.idade, p.peso_kg, p.altura_m, p.imc,
               p.gordura_pct, p.bpm_repouso, p.agua_litros,
               p.treinos_por_semana, p.nivel_experiencia, p.experiencia,
               t.tipo_treino, t.codigo_compendio, t.atividade_compendio,
               t.met, t.met_estimado
        FROM ouro.fato_sessao f
        JOIN ouro.dim_praticante p USING (praticante_id)
        JOIN ouro.dim_treino t USING (treino_id)
    """)


def conferir(con):
    """Aula 9: as conferencias do modelo. Todas precisam dar zero.

    Desde a aula 11 cada uma virou teste do dbt (ecox14/models/schema.yml
    e ecox14/tests/), que falha sozinho e para o pipeline. Fica aqui para
    comparar com a saida do 'dbt test'.
    """
    conferencias = {
        # o grao se confirma? (uma linha por sessao)
        "sessoes repetidas na fato": """
            SELECT COUNT(*) FROM (
                SELECT sessao_id FROM ouro.fato_sessao
                GROUP BY sessao_id HAVING COUNT(*) > 1)""",
        # um treino por linha na dimensao?
        "treinos repetidos na dim_treino": """
            SELECT COUNT(*) FROM (
                SELECT treino_id FROM ouro.dim_treino
                GROUP BY treino_id HAVING COUNT(*) > 1)""",
        # sobrou fato sem dimensao?
        "fatos sem treino na dimensao": """
            SELECT COUNT(*) FROM ouro.fato_sessao f
            LEFT JOIN ouro.dim_treino t USING (treino_id)
            WHERE t.treino_id IS NULL""",
        "fatos sem praticante na dimensao": """
            SELECT COUNT(*) FROM ouro.fato_sessao f
            LEFT JOIN ouro.dim_praticante p USING (praticante_id)
            WHERE p.praticante_id IS NULL""",
        # quantas sessoes da prata ficaram fora da fato?
        "sessoes da prata fora da fato": """
            SELECT (SELECT COUNT(*) FROM prata.gym_members_enriquecida)
                 - (SELECT COUNT(*) FROM ouro.fato_sessao)""",
    }
    resultado = {}
    for nome, sql in conferencias.items():
        valor = um_valor(con, sql)
        resultado[nome] = valor
        if valor:
            log.warning("%s: %d", nome, valor)
        else:
            log.info("%s: 0", nome)
    return resultado


def main():
    con = conectar()
    try:
        criar_esquemas(con)
        carregar_prata(con)
        # construir_ouro(con)   <- aula 10: agora e o dbt (ecox14/)
        # conferir(con)         <- aula 11: agora sao testes do dbt
    finally:
        # Fechar libera o arquivo: o dbt, na etapa seguinte, abre o
        # mesmo banco, e o DuckDB nao deixa dois programas escreverem.
        con.close()
    log.info("banco: %s", BANCO.name)


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()
