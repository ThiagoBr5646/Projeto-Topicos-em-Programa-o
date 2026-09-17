from pathlib import Path

import pandas as pd
from data_profiling import ProfileReport

# ---- Fonte: Gym Members Exercise Dataset (Kaggle) ----
BRONZE = Path("dados/bronze/gym_members")
PADRAO = "gym_members_exercise_tracking_*.csv"
RELATORIOS = Path("relatorios")


def mais_recente():
    """Retorna o arquivo mais novo da bronze, assumindo nomes com data
    no formato ano-mes-dia (ordem alfabética = ordem cronológica)."""
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError("bronze vazia")
    return arquivos[-1]


def gerar(caminho):
    """Lê o CSV e gera o relatório de profiling em HTML."""
    df = pd.read_csv(caminho)
    perfil = ProfileReport(df, title=caminho.name)
    RELATORIOS.mkdir(exist_ok=True)
    saida = RELATORIOS / f"{caminho.stem}.html"
    perfil.to_file(saida)
    return saida


def main():
    caminho = mais_recente()
    print("perfilando:", caminho.name)
    print(gerar(caminho))


if __name__ == "__main__":
    main()