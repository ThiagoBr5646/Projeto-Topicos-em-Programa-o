"""Consultas de leitura do painel: uma funcao por pergunta.

Aula 11 - Testes, documentacao e entrega do dado (ECOX14).

Onde mora cada SQL do projeto:
    cria tabela (dim, fato, view)    -> ecox14/models, no dbt, testado
    consulta de leitura              -> aqui
    a tela                           -> dashboard/painel.py, sem SQL

O teste para uma consulta morar aqui: se alguem pedir o mesmo numero por
e-mail, sem abrir o painel, da para chamar a funcao direto do Python.

Todo valor que vem da tela entra como parametro (?), nunca concatenado
no texto do SQL: o banco nunca o interpreta como comando.

Este modulo so le. A conexao e read_only e abre e fecha a cada
consulta: o painel aberto nao segura o arquivo do banco, e o pipeline
(dbt) consegue gravar enquanto ele esta no ar.
"""
from pathlib import Path
import json

import duckdb

# O caminho vem do proprio arquivo, igual ao config.py. O painel nao
# importa o config: ele fica fora do pipeline, e o pipeline nao sabe que
# ele existe.
RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "dados" / "ouro" / "projeto.duckdb"
BRONZE = RAIZ / "dados" / "bronze"

# Valor dos filtros que significa "sem filtro".
TODOS = "Todos"

# Caracteristicas numericas que a pergunta norteadora pode testar:
# coluna da view -> nome para exibir.
CARACTERISTICAS = {
    "duracao_h": "Duração da sessão",
    "bpm_medio": "BPM médio na sessão",
    "bpm_max": "BPM máximo na sessão",
    "idade": "Idade",
    "peso_kg": "Peso",
    "imc": "IMC",
    "gordura_pct": "% de gordura",
    "bpm_repouso": "BPM em repouso",
    "agua_litros": "Água por dia",
    "treinos_por_semana": "Treinos por semana",
    "nivel_experiencia": "Nível de experiência",
    "met": "MET do treino (Compêndio)",
}

# Filtro comum a quase todas as consultas: "Todos" desliga cada um.
# Cada filtro usa o parametro duas vezes (? = 'Todos' or coluna = ?).
FILTRO = """
    (? = 'Todos' or tipo_treino = ?)
    and (? = 'Todos' or genero = ?)
    and (? = 'Todos' or experiencia = ?)
"""


def _consultar(sql, parametros=None):
    """Roda uma consulta de leitura e devolve um DataFrame."""
    if not BANCO.exists():
        raise FileNotFoundError(
            f"{BANCO} nao existe: rode antes python src/pipeline.py")
    con = duckdb.connect(str(BANCO), read_only=True)
    try:
        return con.execute(sql, parametros or []).df()
    finally:
        con.close()


def _parametros(tipo_treino, genero, experiencia):
    """Os tres filtros, cada um repetido (o FILTRO usa cada ? duas vezes)."""
    return [tipo_treino, tipo_treino, genero, genero, experiencia, experiencia]


# ---- Opcoes dos filtros ---------------------------------------------
def tipos_treino():
    """Tipos de treino que existem na dimensao."""
    return _consultar(
        "select tipo_treino from ouro.dim_treino order by tipo_treino")


def generos():
    """Generos que existem na dimensao."""
    return _consultar(
        "select distinct genero from ouro.dim_praticante order by genero")


def niveis_experiencia():
    """Rotulos de experiencia, na ordem do nivel (nao alfabetica)."""
    return _consultar("""
        select distinct nivel_experiencia, experiencia
        from ouro.dim_praticante
        order by nivel_experiencia
    """)


# ---- Perguntas ------------------------------------------------------
def resumo(tipo_treino=TODOS, genero=TODOS, experiencia=TODOS):
    """Sessoes e calorias medias (base e Compendio) do recorte escolhido."""
    return _consultar(f"""
        select
            count(*)                        as sessoes,
            round(avg(calorias_base), 0)    as kcal_base,
            round(avg(calorias_met), 0)     as kcal_compendio,
            round(median(razao_base_met), 2) as razao_mediana
        from ouro.vw_sessao_completa
        where {FILTRO}
    """, _parametros(tipo_treino, genero, experiencia))


def explicacao_por_caracteristica(tipo_treino=TODOS, genero=TODOS,
                                  experiencia=TODOS):
    """A pergunta norteadora: quanto cada caracteristica explica, sozinha,
    das calorias da base (R2 de uma reta, em %).

    Uma consulta por caracteristica, unidas: o nome da coluna nao pode
    ser parametro (parametro so substitui valor), entao ele vem da lista
    fixa CARACTERISTICAS, escrita aqui - nunca da tela.
    """
    partes = [
        f"select '{rotulo}' as caracteristica, "
        f"round(100 * power(corr(calorias_base, {coluna}), 2), 1) as r2_pct "
        f"from ouro.vw_sessao_completa where {FILTRO}"
        for coluna, rotulo in CARACTERISTICAS.items()
    ]
    # Coluna constante no recorte (o MET quando se filtra um treino so)
    # nao tem correlacao: o corr devolve NaN, que vira nulo e vai pro fim.
    sql = f"""
        select caracteristica,
               case when isnan(r2_pct) then null else r2_pct end as r2_pct
        from ({" union all ".join(partes)})
        order by r2_pct desc nulls last
    """
    parametros = _parametros(tipo_treino, genero, experiencia) * len(partes)
    return _consultar(sql, parametros)


def base_x_compendio(genero=TODOS, experiencia=TODOS):
    """Por tipo de treino: kcal/h que a base da x kcal/h que o Compendio
    espera para o mesmo peso (MET x peso). Nao filtra por treino: o tipo
    de treino e o eixo da comparacao."""
    return _consultar(f"""
        select
            tipo_treino,
            any_value(met)                            as met,
            count(*)                                  as sessoes,
            round(avg(calorias_por_hora), 1)          as kcal_h_base,
            round(avg(met * peso_kg), 1)              as kcal_h_compendio,
            round(avg(calorias_por_hora) / avg(met * peso_kg), 2)
                                                      as base_sobre_compendio
        from ouro.vw_sessao_completa
        where {FILTRO}
        group by tipo_treino
        order by tipo_treino
    """, _parametros(TODOS, genero, experiencia))


def sessoes(tipo_treino=TODOS, genero=TODOS, experiencia=TODOS):
    """As sessoes do recorte, uma por linha, com o que a pergunta usa."""
    return _consultar(f"""
        select
            sessao_id, tipo_treino, genero, idade, experiencia, peso_kg,
            duracao_h, bpm_medio, calorias_base, calorias_met,
            calorias_por_hora, razao_base_met
        from ouro.vw_sessao_completa
        where {FILTRO}
        order by sessao_id
    """, _parametros(tipo_treino, genero, experiencia))


# ---- De onde veio ----------------------------------------------------
def proveniencia():
    """Fonte e data de extracao de cada fonte, lidas da proveniencia da
    bronze (aula 3). Nao e SQL, mas e acesso a dado: mora aqui tambem."""
    fontes = {}
    for pasta in ("gym_members", "compendio"):
        arquivo = BRONZE / pasta / "proveniencia.json"
        if arquivo.exists():
            info = json.loads(arquivo.read_text(encoding="utf-8"))
            fontes[pasta] = {
                "fonte": info.get("fonte", ""),
                "extraido_em": info.get("extraido_em", "")[:10],
            }
    return fontes
