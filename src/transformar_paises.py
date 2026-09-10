"""Transforma a camada Bronze de paises (Banco Mundial) na camada Prata.

Aula 5 - Qualidade de dados (Topicos em Programacao / ECOX14).

Le o CSV mais recente da bronze, aplica limpeza e checagens de qualidade,
compara dois metodos de deteccao de valor extremo, remove so o erro
comprovado pelo dominio, e grava o resultado em Parquet na prata.
"""
from datetime import datetime
from pathlib import Path
import json

import pandas as pd

BRONZE = Path("dados/bronze/banco_mundial")
PRATA = Path("dados/prata")
PADRAO = "paises_*.csv"

# Faixa geografica valida: fora disso e impossibilidade, nao estatistica.
LIMITES_GEOGRAFICOS = {
    "longitude": (-180, 180),
    "latitude": (-90, 90),
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


def tirar_espacos(df):
    """Remove espacos sobrando dos nomes de coluna e do conteudo texto.

    Defeito anotado na fonte: valores de regiao como
    'Latin America & Caribbean ' vem com espaco no fim.
    """
    df.columns = df.columns.str.strip()
    for coluna in df.select_dtypes(include=["object", "string"]):
        df[coluna] = df[coluna].str.strip()
    return df


def separar_agregados(df):
    """Separa os agregados regionais (World, Africa, ...) dos paises reais.

    Isso nao e limpeza de erro: agregado e dado correto, so que em outra
    granularidade. Misturar os dois numa soma e que seria o erro.
    """
    e_pais = df["region.value"] != "Aggregates"
    print("paises   :", e_pais.sum())
    print("agregados:", (~e_pais).sum())
    return df[e_pais].copy()


def conferir_chave(df, chave="id"):
    """Confere se a chave declarada no README (codigo de 3 letras do
    pais) esta mesmo unica apos separar os agregados."""
    repetidas = df[chave].duplicated().sum()
    print("chaves repetidas:", repetidas)
    if repetidas:
        print(df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


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

    df = tirar_espacos(df)
    df = separar_agregados(df)
    df = conferir_chave(df)
    df, novos_ausentes = converter_tipos(df)

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
        "Chave 'id' conferida quanto a duplicidade apos separar os agregados.",
        "Longitude e latitude convertidas para numero; "
        f"vazios/invalidos viraram ausentes: {novos_ausentes}.",
        "Valores extremos de longitude e latitude marcados por dois metodos "
        f"(IQR e z-score, limite 3), para comparar: {contagens_extremos}. "
        "Nenhum extremo foi removido, so sinalizado.",
        "Linhas com longitude ou latitude fora da faixa geografica valida "
        f"removidas por erro comprovado: {removidas_por_erro}.",
        "Coluna capitalCity vazia mantida como esta: nao se aplica a "
        "todos os registros e o vazio aqui e a resposta certa.",
    ]
    info = registrar(origem, destino, antes, depois, decisoes)

    print("concluido:", destino)
    print("linhas: antes =", antes, "| depois =", depois)
    return info


if __name__ == "__main__":
    main()
