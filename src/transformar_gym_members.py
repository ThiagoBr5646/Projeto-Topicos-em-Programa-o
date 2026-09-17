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

Como executar, a partir da raiz do projeto:
    python src/transformar_gym_members.py
"""
from datetime import datetime
from pathlib import Path
import json

import pandas as pd

import limpeza  # modulo do projeto, em src/

BRONZE = Path("dados/bronze/gym_members")
PRATA = Path("dados/prata")
PADRAO = "gym_members_exercise_tracking_*.csv"

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
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    print("lido:", caminho.name, df.shape)
    return df, caminho


def olhar_antes_de_decidir(df):
    """Mostra colunas e ausentes antes de qualquer alteracao."""
    print(df.columns.tolist())
    print(df.isna().sum().to_dict())


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
        print(coluna, "->", list(df[coluna].cat.categories))

    df["experiencia"] = pd.Categorical(
        df["Experience_Level"].map(ROTULO_EXPERIENCIA),
        categories=ORDEM_EXPERIENCIA,
        ordered=True,
    )
    fora_da_escala = int(df["experiencia"].isna().sum())
    print("experiencia fora da escala:", fora_da_escala)
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

    print("sessoes com duracao invalida (viraram ausentes):", sem_duracao)
    print(df["calorias_por_hora"].describe().round(1).to_dict())
    return df, sem_duracao


def conferir_plausibilidade(df):
    """Confere se o atributo novo tem valor plausivel.

    Nao e teste automatizado, e conferencia antes de commitar: kcal/h
    de treino de gente adulta cai, grosso modo, entre 200 e 1500. O que
    passar disso nao e removido, e sinalizado - remover exige dono.
    """
    faixa = (200, 1500)
    fora = df["calorias_por_hora"].notna() & ~df["calorias_por_hora"].between(*faixa)
    print("calorias_por_hora fora de", faixa, ":", int(fora.sum()))
    if fora.any():
        print(df.loc[fora, [CALORIAS, DURACAO, "calorias_por_hora"]].head())
    return int(fora.sum())


def salvar(df):
    """Grava a prata em Parquet, sem data no nome: a prata e
    reconstruivel, cada execucao substitui a versao anterior."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "gym_members.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    """Registra a proveniencia no mesmo arquivo das outras fontes."""
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
    repetidas = int(df.duplicated().sum())
    print("linhas identicas repetidas:", repetidas)
    df = df.drop_duplicates()

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
        f"Conferencia de plausibilidade de calorias_por_hora (200 a 1500 "
        f"kcal/h): {fora_da_faixa} fora da faixa, sinalizadas e nao "
        "removidas.",
        "PENDENTE desta fonte: as checagens de qualidade da aula 5 "
        "(valor extremo por IQR e z-score, faixa valida por dominio) "
        "foram feitas so na fonte de paises; esta prata cobre a limpeza "
        "e o atributo derivado da aula 6.",
    ]
    info = registrar(origem, destino, antes, depois, decisoes)

    print("concluido:", destino)
    print("linhas: antes =", antes, "| depois =", depois)
    return info


if __name__ == "__main__":
    main()
