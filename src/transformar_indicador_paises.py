"""Transforma a Bronze do indicador por pais e por ano na camada Prata.

Aula 6 - Limpeza avancada e engenharia de atributos (ECOX14).

Esta e a terceira fonte do projeto, e a unica que tem tempo. Sem tempo
nao se pergunta se algo cresceu, quando mudou de patamar, ou o que veio
antes e o que veio depois - e boa parte das perguntas interessantes e
sobre variacao.

Serie usada: SH.XPD.CHEX.PC.CD (gasto corrente em saude per capita, em
dolares), 2000 a 2023, por pais.

O que este script resolve:
    1. o ano fica inteiro, nao data (um ano nao tem mes, dia nem hora);
    2. as colunas sem informacao saem, contadas e registradas;
    3. dois atributos derivados: variacao anual e faixa por quartil.

O que ele NAO resolve, de proposito: os agregados regionais (World,
Africa Eastern..., High income) continuam na tabela. Nesta fonte nao
existe coluna de regiao para filtra-los, e a resposta esta na juncao
com a prata de paises - assunto da proxima aula. Fica registrado na
proveniencia como defeito conhecido, nao como esquecimento.

Como executar, a partir da raiz do projeto:
    python src/transformar_indicador_paises.py
"""
from datetime import datetime
from pathlib import Path
import json

import pandas as pd

import limpeza  # modulo do projeto, em src/

INDICADOR = "SH.XPD.CHEX.PC.CD"
BRONZE = Path("dados/bronze/banco_mundial/indicador_paises")
PRATA = Path("dados/prata")
PADRAO = f"{INDICADOR}_*.csv"

# Granularidade desta tabela: uma linha por pais e por ano. A chave nao
# e countryiso3code direto porque a fonte deixa esse campo vazio em
# parte dos agregados - ver criar_codigo().
CHAVES = ["pais_codigo", "date"]

# Colunas que a API manda sempre e que nesta serie nao carregam
# informacao nenhuma: unit e obs_status vem vazias, decimal vem sempre
# com o mesmo valor. indicator.id e indicator.value tambem sao
# constantes, mas ficam: elas dizem QUAL serie e esta, e isso e
# metadado proposital, nao coluna inutil.
CANDIDATAS_A_SAIR = ["unit", "obs_status", "decimal"]

# Rotulos da faixa por quartil. Sao do assunto desta fonte (gasto em
# saude), por isso moram aqui e nao no modulo.
ROTULOS_FAIXA = ["muito baixo", "baixo", "alto", "muito alto"]


def carregar():
    """Le o arquivo mais recente da bronze (a data no nome ordena).

    keep_default_na=False nao e detalhe: o codigo de 2 letras da
    Namibia e 'NA', e o pandas, na configuracao padrao, le 'NA' como
    ausente. A Namibia chegava aqui sem codigo por causa da biblioteca,
    nao por causa da fonte. Desligando a lista padrao, so a celula
    vazia conta como ausente - que e exatamente o que esta API escreve
    quando nao tem o valor.
    """
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(
            f"nada em {BRONZE} - rode antes: python src/ingerir_indicador_paises.py"
        )
    caminho = arquivos[-1]
    df = pd.read_csv(caminho, keep_default_na=False, na_values=[""])
    print("lido:", caminho.name, df.shape)
    return df, caminho


def olhar_antes_de_decidir(df):
    """Mostra colunas, tipos e celulas sem conteudo antes de qualquer
    alteracao.

    Conta vazio junto com ausente: depois de keep_default_na=False, o
    que a fonte manda em branco chega como texto vazio, e um
    isna().sum() puro diria que nao falta nada.
    """
    print(df.columns.tolist())
    print(df.dtypes)
    vazias = {}
    for coluna in df.columns:
        serie = df[coluna]
        if str(serie.dtype) in ("object", "string"):
            serie = serie.astype("string").str.strip().replace("", pd.NA)
        vazias[coluna] = int(serie.isna().sum())
    print("sem conteudo (ausente ou vazio):", vazias)


def criar_codigo(df):
    """Cria a coluna de codigo do pais que serve de chave.

    Defeito real da fonte: as cinco linhas de agregado por nivel de
    renda (High income, Low income, Lower middle, Upper middle, Not
    classified) vem com countryiso3code vazio, embora tenham codigo de
    2 letras em country.id. Sao 24 anos cada uma.

    Antes desta funcao, a checagem de granularidade via countryiso3code
    acusava 96 chaves 'repetidas' - ausente contra ausente - e apagar
    por essa contagem jogava fora 96 linhas boas de agregado. O
    conserto e dar codigo a elas, nao remove-las: o codigo de 2 letras
    ja esta na resposta.
    """
    fallback = df["countryiso3code"].isna() & df["country.id"].notna()
    df["pais_codigo"] = df["countryiso3code"].fillna(df["country.id"])
    sem_codigo = int(df["pais_codigo"].isna().sum())

    print("codigo preenchido a partir de country.id:", int(fallback.sum()))
    print("linhas ainda sem codigo nenhum          :", sem_codigo)
    if fallback.any():
        print(df.loc[fallback, ["country.id", "country.value"]]
              .drop_duplicates().to_string(index=False))
    return df, int(fallback.sum()), sem_codigo


def tipar(df):
    """Da tipo as duas colunas que se comportam: o ano e o valor.

    O ano vira inteiro, nao data. O valor vira numero, com
    errors='coerce', e contamos quantos viraram ausentes na conversao -
    conversao que come dado em silencio e o defeito que nao avisa.
    """
    df["date"] = limpeza.ano_para_inteiro(df["date"])

    ausentes_antes = int(df["value"].isna().sum())
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    novos_ausentes = int(df["value"].isna().sum()) - ausentes_antes

    print("anos:", int(df["date"].min()), "a", int(df["date"].max()))
    print("valores ausentes na fonte        :", ausentes_antes)
    print("novos ausentes pela conversao    :", novos_ausentes)
    return df, ausentes_antes, novos_ausentes


def variacao_anual(df, chave, tempo, valor):
    """Variacao percentual em relacao ao ano anterior, dentro de cada chave.

    O sort_values nao e enfeite: sem ordenar primeiro, a variacao seria
    calculada contra a linha anterior do arquivo, que pode ser outro ano
    ou outro pais.

    A aula mostra a versao curta, com pct_change(). Aqui a conta e feita
    com shift explicito para poder exigir que o ano anterior seja mesmo
    o ano anterior: quando a serie do pais tem buraco (2010 e depois
    2013), pct_change chamaria isso de variacao de um ano, e nao e. Nessa
    situacao o resultado fica ausente, que e a resposta honesta.

    A variacao do primeiro ano de cada pais nao existe, por definicao.
    """
    df = df.sort_values([chave, tempo]).copy()
    valor_anterior = df.groupby(chave)[valor].shift(1)
    tempo_anterior = df.groupby(chave)[tempo].shift(1)
    consecutivo = (df[tempo] - tempo_anterior) == 1

    df["variacao_pct"] = (
        (df[valor] / valor_anterior - 1) * 100).where(consecutivo)

    print("variacao_pct calculada em:", int(df["variacao_pct"].notna().sum()),
          "de", len(df), "linhas")
    return df


def faixa_por_quartil(df, coluna, rotulos, por=None):
    """Cria faixas por quartil a partir de uma coluna continua.

    qcut corta por quantidade de registros, entao cada faixa fica com um
    quarto dos casos. cut cortaria por valor, em faixas de largura igual.
    Sao resultados diferentes, e a escolha depende da pergunta: aqui
    interessa 'gasta pouco ou muito comparado aos outros', que e posicao
    relativa, logo qcut.

    `por` existe por um motivo de dominio: o gasto esta em dolares
    correntes e sobe com o tempo em quase todo pais. Um quartil calculado
    sobre o painel inteiro misturaria decadas e diria que 2001 gasta
    pouco. Cortando ano a ano, cada pais e comparado com os
    contemporaneos dele.

    A faixa e categoria COM ordem: sem declarar a ordem, o pandas
    ordenaria em ordem alfabetica e 'muito alto' viria antes de 'baixo'.
    """
    nova = coluna + "_faixa"
    sem_corte = []

    def cortar(serie):
        """Corta um grupo em quartis, ou devolve tudo ausente quando o
        grupo nao tem valores distintos suficientes.

        O ultimo ano da serie costuma vir inteiro sem dado. Forcar o
        corte ali daria erro; inventar faixa daria numero errado. Deixar
        ausente e a resposta honesta, e a contagem abaixo diz em quantos
        grupos isso aconteceu.
        """
        if serie.dropna().nunique() < len(rotulos):
            sem_corte.append(len(serie))
            return pd.Series(pd.NA, index=serie.index, dtype="object")
        return pd.qcut(serie, q=len(rotulos), labels=rotulos).astype("object")

    if por is None:
        df[nova] = cortar(df[coluna])
    else:
        df[nova] = df.groupby(por, observed=True, group_keys=False)[
            coluna].apply(cortar)

    df[nova] = pd.Categorical(df[nova], categories=rotulos, ordered=True)

    if sem_corte:
        print("grupos sem dado suficiente para quartil:", len(sem_corte))
    print(df[nova].value_counts(dropna=False))
    return df, len(sem_corte)


def conferir_plausibilidade(df, limite=100):
    """Confere se a variacao calculada tem valor plausivel.

    A aula avisa: variacao de 4000% costuma ser divisao por um valor
    quase zero, nao noticia economica. Aqui o maior salto vem de
    crise cambial em serie medida em dolar corrente (Argentina em 2002,
    por exemplo), o que e variacao de verdade. Nada e removido: a
    conferencia existe para o numero absurdo aparecer antes do commit,
    nao para apagar linha.
    """
    fora = df["variacao_pct"].abs() > limite
    print(f"|variacao_pct| > {limite}%:", int(fora.sum()))
    if fora.any():
        print(df.loc[fora, ["country.value", "date", "value", "variacao_pct"]]
              .head(10).to_string(index=False))
    return int(fora.sum())


def salvar(df):
    """Grava a prata em Parquet, sem data no nome: a prata e
    reconstruivel, cada execucao substitui a versao anterior."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "indicador_paises.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    """Registra a proveniencia da transformacao, no mesmo arquivo das
    outras fontes: as decisoes tomadas no caminho, nao so o resultado."""
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

    df = limpeza.tirar_espacos(df)
    df, vazias, constantes = limpeza.remover_colunas_sem_informacao(
        df, CANDIDATAS_A_SAIR)
    df, ausentes_na_fonte, novos_ausentes = tipar(df)
    df, codigo_do_fallback, sem_codigo = criar_codigo(df)
    df, repetidas, ausentes_na_chave = limpeza.conferir_chave_composta(
        df, CHAVES)
    if repetidas:
        raise ValueError(
            f"granularidade quebrada: {repetidas} pares {CHAVES} repetidos. "
            "Uma linha por pais e por ano era a premissa desta tabela; "
            "parar aqui e melhor que seguir com a tabela errada."
        )

    # chave de texto do nome do pais, para a juncao da proxima aula:
    # o codigo de 3 letras e a chave boa, e o nome serve de conferencia
    df["pais_chave"] = limpeza.chave_texto(df["country.value"])

    # atributos derivados
    df = variacao_anual(df, "pais_codigo", "date", "value")
    df, grupos_sem_quartil = faixa_por_quartil(
        df, "value", ROTULOS_FAIXA, por="date")
    variacoes_extremas = conferir_plausibilidade(df)

    depois = len(df)
    destino = salvar(df)

    decisoes = [
        f"Serie {INDICADOR} (gasto corrente em saude per capita, USD), "
        "ingerida com todas as paginas percorridas.",
        "Espacos removidos de nomes de coluna e de texto "
        "(src/limpeza.tirar_espacos).",
        f"Colunas sem informacao removidas - vazias: {vazias}; "
        f"constantes: {constantes}. indicator.id e indicator.value sao "
        "constantes e ficaram, porque identificam a serie.",
        "Coluna 'date' convertida para inteiro (Int64), nao para data: "
        "um ano nao tem mes, dia, hora nem fuso, e converter para data "
        "acrescentaria precisao falsa.",
        f"Coluna 'value' convertida para numero; ausentes que ja vinham da "
        f"fonte: {ausentes_na_fonte}; novos ausentes pela conversao: "
        f"{novos_ausentes}.",
        "Arquivo lido com keep_default_na=False: o codigo de 2 letras da "
        "Namibia e 'NA' e o pandas o lia como ausente na configuracao "
        "padrao. Somente celula vazia conta como ausente nesta fonte.",
        "Coluna pais_codigo criada como chave: countryiso3code, preenchida "
        "com country.id onde a fonte deixou o iso3 vazio (os cinco "
        f"agregados por nivel de renda) - {codigo_do_fallback} linhas pelo "
        f"fallback, {sem_codigo} ainda sem codigo nenhum.",
        f"Granularidade conferida em {CHAVES}: {repetidas} chaves repetidas "
        f"entre as linhas com chave completa; ausentes na chave: "
        f"{ausentes_na_chave}. Nada foi removido por duplicidade - chave "
        "ausente conta como repetida no pandas, e apagar por essa contagem "
        "jogaria fora linha boa de agregado.",
        "DEFEITO CONHECIDO mantido: os agregados regionais (World, "
        "High income, Africa Eastern...) continuam na tabela. Esta fonte "
        "nao tem coluna de regiao para filtra-los; a separacao sai da "
        "juncao com dados/prata/paises.parquet.",
        "Atributo derivado variacao_pct: variacao percentual do indicador "
        "em relacao ao ano anterior, por pais. Ausente no primeiro ano de "
        "cada pais e quando ha buraco na serie (o ano anterior nao e "
        f"consecutivo). Conferencia de plausibilidade: {variacoes_extremas} "
        "linhas com |variacao| acima de 100%, sinalizadas e nao removidas "
        "(a serie esta em dolar corrente, e crise cambial produz salto "
        "grande de verdade).",
        "Atributo derivado value_faixa: quartil do gasto per capita "
        f"calculado ano a ano ({ROTULOS_FAIXA}), como categoria ordenada. "
        "Ano a ano porque o valor esta em dolares correntes e sobe com o "
        "tempo; quartil do painel inteiro compararia decadas diferentes. "
        f"Anos sem dado suficiente para cortar em quartis (faixa ausente): "
        f"{grupos_sem_quartil}.",
    ]
    info = registrar(origem, destino, antes, depois, decisoes)

    print("concluido:", destino)
    print("linhas: antes =", antes, "| depois =", depois)
    return info


if __name__ == "__main__":
    main()
