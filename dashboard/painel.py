"""Painel do projeto: a camada Ouro na frente de quem precisa dela.

Aula 11 - Testes, documentacao e entrega do dado (ECOX14).

So a tela: nenhuma linha de SQL. Cada numero vem de uma funcao de
dashboard/consultas.py. O painel e consumidor - le a Ouro e nao escreve
nada -, por isso fica fora de src/ e fora do pipeline.

Como executar, a partir da raiz do projeto (depois do pipeline):
    python -m streamlit run dashboard/painel.py
Para parar: Ctrl+C no terminal.
"""
import streamlit as st

import consultas

st.set_page_config(page_title="Calorias na academia", layout="wide")
st.title("O que explica as calorias de uma sessão de academia?")

# ---- Filtros ----------------------------------------------------------
TODOS = consultas.TODOS
st.sidebar.header("Filtros")
tipo_treino = st.sidebar.selectbox(
    "Tipo de treino", [TODOS, *consultas.tipos_treino()["tipo_treino"]])
genero = st.sidebar.selectbox(
    "Gênero", [TODOS, *consultas.generos()["genero"]])
experiencia = st.sidebar.selectbox(
    "Experiência", [TODOS, *consultas.niveis_experiencia()["experiencia"]])

resumo = consultas.resumo(tipo_treino, genero, experiencia).iloc[0]
if resumo["sessoes"] == 0:
    st.warning("Nenhuma sessão neste recorte. Afrouxe um dos filtros.")
    st.stop()

# ---- Resumo do recorte -------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Sessões", int(resumo["sessoes"]))
c2.metric("kcal por sessão (base)", f"{resumo['kcal_base']:.0f}")
c3.metric("kcal por sessão (Compêndio)", f"{resumo['kcal_compendio']:.0f}")
c4.metric("Base ÷ Compêndio (mediana)", f"{resumo['razao_mediana']:.2f}")

# ---- Pergunta norteadora ------------------------------------------------
st.subheader("Quanto cada característica explica, sozinha, das calorias da base")
explicacao = consultas.explicacao_por_caracteristica(
    tipo_treino, genero, experiencia)
col1, col2 = st.columns([3, 2])
with col1:
    st.bar_chart(explicacao, x="caracteristica", y="r2_pct",
                 x_label="R² (%)", y_label="", horizontal=True,
                 sort="-r2_pct")
with col2:
    st.dataframe(explicacao, hide_index=True,
                 column_config={"caracteristica": "Característica",
                                "r2_pct": "R² (%)"})
st.caption("R² de uma reta entre a característica e as calorias da base. "
           "Vazio quando a característica não varia no recorte.")

# ---- Base x Compêndio ----------------------------------------------------
st.subheader("kcal/h por tipo de treino: o que a base dá × o que o Compêndio espera")
comparacao = consultas.base_x_compendio(genero, experiencia)
col1, col2 = st.columns([3, 2])
with col1:
    st.bar_chart(comparacao, x="tipo_treino",
                 y=["kcal_h_base", "kcal_h_compendio"],
                 x_label="", y_label="kcal/h", stack=False)
with col2:
    st.dataframe(comparacao, hide_index=True,
                 column_config={"tipo_treino": "Treino", "met": "MET",
                                "sessoes": "Sessões",
                                "kcal_h_base": "kcal/h base",
                                "kcal_h_compendio": "kcal/h Compêndio",
                                "base_sobre_compendio": "Base ÷ Compêndio"})
st.caption("kcal/h esperada = MET do treino × peso do praticante "
           "(1 MET ≈ 1 kcal por kg por hora). Este gráfico não usa o filtro "
           "de tipo de treino: o treino é o eixo da comparação.")

# ---- Detalhe ---------------------------------------------------------------
st.subheader("Sessões do recorte")
detalhe = consultas.sessoes(tipo_treino, genero, experiencia)
st.dataframe(detalhe, hide_index=True)

# ---- De onde veio ------------------------------------------------------------
fontes = consultas.proveniencia()
academia = fontes.get("gym_members", {})
compendio = fontes.get("compendio", {})
st.caption(
    f"Fonte: Gym Members Exercise Dataset (Kaggle, {academia.get('fonte', '?')}), "
    f"extraído em {academia.get('extraido_em', '?')}; MET do 2024 Adult "
    f"Compendium of Physical Activities, extraído em "
    f"{compendio.get('extraido_em', '?')}. {len(detalhe)} registros. "
    "Atenção: a base da academia é sintética - as calorias seguem uma fórmula "
    "de duração, BPM médio, gênero e idade (README, 'Defeitos conhecidos das "
    "fontes'). Os números descrevem o gerador dos dados, não praticantes reais.")
