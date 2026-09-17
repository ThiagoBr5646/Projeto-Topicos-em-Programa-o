"""Transforma a camada Bronze de paises (Banco Mundial) na camada Prata.

Aula 5 - Qualidade de dados (Topicos em Programacao / ECOX14).
Aula 6 - Limpeza avancada: as funcoes genericas sairam deste arquivo e
         passaram a morar em src/limpeza.py; ficaram aqui so as que
         mencionam o nome da fonte (nivel de renda do Banco Mundial).

Le o CSV mais recente da bronze, aplica limpeza e checagens de qualidade,
compara dois metodos de deteccao de valor extremo, remove so o erro
comprovado pelo dominio, tipa o nivel de renda como categoria ordenada
e grava o resultado em Parquet na prata.

Como executar, a partir da raiz do projeto:
    python src/transformar_paises.py
"""
from datetime import datetime
from pathlib import Path
import json

import pandas as pd

import limpeza  # modulo do projeto, em src/

BRONZE = Path("dados/bronze/banco_mundial")
PRATA = Path("dados/prata")
PADRAO = "paises_*.csv"

# Faixa geografica valida: fora disso e impossibilidade, nao estatistica.
LIMITES_GEOGRAFICOS = {
    "longitude": (-180, 180),
    "latitude": (-90, 90),
}

# A escala de renda tem ordem natural, e declarar isso faz comparar e
# ordenar funcionarem. Sem ordem declarada o pandas ordena em ordem
# alfabetica, e 'High income' vem primeiro.
ORDEM_RENDA = [
    "Low income",
    "Lower middle income",
    "Upper middle income",
    "High income",
]

# Dicionario de sinonimos: especifico desta fonte, por isso mora aqui e
# nao no modulo. As chaves estao na forma comparavel (sem acento, em
# minuscula), que e o que limpeza.chave_texto devolve.
#
# Variantes reais: a classificacao do Banco Mundial ja usou
# 'High income: OECD' e 'High income: nonOECD' como categorias
# separadas, e a forma com hifen aparece em extracoes mais antigas.
# Escrever o mapa deixa o script funcionar tambem sobre uma bronze
# antiga, em vez de jogar essas linhas fora em silencio.
MAPA_RENDA = {
    "high income: oecd": "high income",
    "high income: nonoecd": "high income",
    "upper-middle income": "upper middle income",
    "lower-middle income": "lower middle income",
}

# Da forma comparavel de volta para o rotulo canonico que aparece em
# ORDEM_RENDA. O que nao estiver aqui (por exemplo 'Not classified')
# nao e nivel de renda, e vira ausente ao declarar a escala.
ROTULO_RENDA = {
    "low income": "Low income",
    "lower middle income": "Lower middle income",
    "upper middle income": "Upper middle income",
    "high income": "High income",
}


def carregar():
    """Le o arquivo mais recente da bronze (a data no nome ordena)."""
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    print("lido:", caminho.name, df.shape)
    return df, caminho


def olhar_antes_de_decidir(df):
    """Mostra colunas e ausentes antes de qualquer alteracao, so para
    conferencia visual (nao transforma nada)."""
    print(df.columns.tolist())
    print(df.isna().sum())


def separar_agregados(df):
    """Separa os agregados regionais (World, Africa, ...) dos paises reais.

    Isso nao e limpeza de erro: agregado e dado correto, so que em outra
    granularidade. Misturar os dois numa soma e que seria o erro.
    """
    e_pais = df["region.value"] != "Aggregates"
    print("paises   :", e_pais.sum())
    print("agregados:", (~e_pais).sum())
    return df[e_pais].copy()


def criar_chaves_de_texto(df):
    """Cria as colunas de comparacao das duas categorias desta fonte.

    O rotulo original fica na tabela, do lado. Uma coluna serve para
    comparar e juntar; a outra, para mostrar.
    """
    df["regiao_chave"] = limpeza.chave_texto(df["region.value"])
    df["renda_chave"] = limpeza.aplicar_mapa(
        limpeza.chave_texto(df["incomeLevel.value"]), MAPA_RENDA
    )
    print("regioes distintas (pelo rotulo) :", df["region.value"].nunique())
    print("regioes distintas (pela chave)  :", df["regiao_chave"].nunique())
    return df


def tipar_renda(df):
    """Tipa o nivel de renda como categoria COM ordem.

    A coluna original e texto livre: nada impede um 'Hgih income' de
    entrar. Declarando a escala, o que nao esta nela vira ausente - e e
    isso que se quer, porque 'Not classified' nao e nivel de renda. O
    codigo passa a dizer em voz alta o que estava escondido no meio do
    texto.

    O rotulo original nao e sobrescrito: a coluna nova se chama
    nivel_renda e fica ao lado de incomeLevel.value, para nao perder a
    informacao de quem caiu fora da escala.
    """
    canonico = limpeza.aplicar_mapa(df["renda_chave"], ROTULO_RENDA)
    ausentes_antes = int(canonico.isna().sum())
    df["nivel_renda"] = pd.Categorical(
        canonico, categories=ORDEM_RENDA, ordered=True)
    fora_da_escala = int(df["nivel_renda"].isna().sum()) - ausentes_antes
    print("renda fora da escala:", fora_da_escala)
    print(df["nivel_renda"].value_counts(dropna=False))
    return df, fora_da_escala


def converter_tipos(df):
    """Converte longitude e latitude de texto para numero.

    errors='coerce' transforma em ausente o que nao for convertivel, em
    vez de derrubar o script. E uma decisao, nao um detalhe: estamos
    escolhendo perder o valor invalido em silencio, por isso contamos
    quantos viraram ausentes logo em seguida.
    """
    ausentes_antes = {c: int(df[c].isna().sum()) for c in LIMITES_GEOGRAFICOS}
    for coluna in LIMITES_GEOGRAFICOS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    novos_ausentes = {
        c: int(df[c].isna().sum()) - ausentes_antes[c] for c in LIMITES_GEOGRAFICOS
    }
    print("novos ausentes por conversao:", novos_ausentes)
    return df, novos_ausentes


def limites_iqr(serie):
    """Limites pelo intervalo interquartil: fora de
    [Q1 - 1.5*IQR, Q3 + 1.5*IQR] e candidato a valor extremo."""
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_extremos_iqr(df, coluna):
    """Marca como extremo (metodo IQR) o que cair fora da faixa do meio."""
    baixo, alto = limites_iqr(df[coluna].dropna())
    df[coluna + "_extremo_iqr"] = (df[coluna] < baixo) | (df[coluna] > alto)
    total = int(df[coluna + "_extremo_iqr"].sum())
    print(coluna, "extremos (IQR):", total)
    return df, total


def marcar_extremos_zscore(df, coluna, limite=3):
    """Marca como extremo (escore padronizado) o que estiver a mais de
    `limite` desvios padrao da media."""
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_extremo_z"] = z.abs() > limite
    total = int(df[coluna + "_extremo_z"].sum())
    print(coluna, "extremos (z-score, limite", limite, "):", total)
    return df, total


def remover_erros(df, coluna, minimo, maximo):
    """Remove so o erro comprovado pelo dominio, nao pela estatistica.

    Longitude fora de [-180, 180] e latitude fora de [-90, 90] sao
    impossibilidades geograficas: aqui a remocao se justifica sempre,
    diferente do valor extremo (que so se marca, nunca se remove sem dono).
    """
    valido = df[coluna].between(minimo, maximo) | df[coluna].isna()
    removidas = int((~valido).sum())
    print("removidas por erro geografico (" + coluna + "):", removidas)
    return df[valido].copy(), removidas


def salvar(df):
    """Grava a prata em Parquet, sem data no nome: a prata e reconstruivel,
    cada execucao substitui a versao anterior pela mais atual."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "paises.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    """Registra a proveniencia da transformacao: as decisoes tomadas no
    caminho, nao so o resultado final."""
    info = {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    return info


def main():
    df, origem = carregar()
    antes = len(df)
    olhar_antes_de_decidir(df)

    # as tres primeiras agora vem do modulo: nenhuma delas menciona
    # Banco Mundial, logo nenhuma delas e desta fonte
    df = limpeza.tirar_espacos(df)
    df = separar_agregados(df)
    df, repetidas, ausentes_na_chave = limpeza.conferir_chave(
        df, "id", remover=True)
    df, novos_ausentes = converter_tipos(df)

    # texto padronizado para comparar, e categoria com ordem declarada
    df = criar_chaves_de_texto(df)
    df, renda_fora_da_escala = tipar_renda(df)

    # duas formas de marcar valor extremo, para comparar (discussao da aula)
    contagens_extremos = {}
    for coluna in LIMITES_GEOGRAFICOS:
        df, n_iqr = marcar_extremos_iqr(df, coluna)
        df, n_z = marcar_extremos_zscore(df, coluna)
        contagens_extremos[coluna] = {"iqr": n_iqr, "zscore": n_z}

    # erro comprovado pelo dominio (nao pela estatistica): fora da faixa
    # geografica valida. Isso e diferente de "extremo", que so se marca.
    removidas_por_erro = {}
    for coluna, (minimo, maximo) in LIMITES_GEOGRAFICOS.items():
        df, n_removidas = remover_erros(df, coluna, minimo, maximo)
        removidas_por_erro[coluna] = n_removidas

    depois = len(df)
    destino = salvar(df)

    # Lista de decisoes com os numeros reais desta execucao (nao
    # hardcoded), porque numeros mudam se a bronze mudar.
    decisoes = [
        "Espacos removidos de nomes de coluna e de texto.",
        "Agregados regionais separados (granularidade diferente da dos paises).",
        "Chave 'id' conferida quanto a duplicidade apos separar os agregados: "
        f"{repetidas} repetidas, {ausentes_na_chave['id']} ausentes na chave.",
        "Longitude e latitude convertidas para numero; "
        f"vazios/invalidos viraram ausentes: {novos_ausentes}.",
        "Valores extremos de longitude e latitude marcados por dois metodos "
        f"(IQR e z-score, limite 3), para comparar: {contagens_extremos}. "
        "Nenhum extremo foi removido, so sinalizado.",
        "Linhas com longitude ou latitude fora da faixa geografica valida "
        f"removidas por erro comprovado: {removidas_por_erro}.",
        "Coluna capitalCity vazia mantida como esta: nao se aplica a "
        "todos os registros e o vazio aqui e a resposta certa.",
        "Funcoes genericas de limpeza passaram a vir de src/limpeza.py "
        "(tirar_espacos, chave_texto, aplicar_mapa, conferir_chave), em vez "
        "de copiadas neste script.",
        "Colunas de comparacao criadas ao lado do rotulo original: "
        "regiao_chave e renda_chave (sem acento, sem espaco, em minuscula).",
        "Nivel de renda tipado como categoria ordenada em nivel_renda "
        f"(Low < Lower middle < Upper middle < High income); linhas fora da "
        f"escala (por exemplo 'Not classified') viraram ausentes: "
        f"{renda_fora_da_escala}.",
    ]
    info = registrar(origem, destino, antes, depois, decisoes)

    print("concluido:", destino)
    print("linhas: antes =", antes, "| depois =", depois)
    return info


if __name__ == "__main__":
    main()
