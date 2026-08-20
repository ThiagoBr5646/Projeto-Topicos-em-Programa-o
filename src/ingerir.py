from pathlib import Path
import shutil
import json
from datetime import date, datetime

import kagglehub

DATASET = "valakhorasani/gym-members-exercise-dataset"
BRONZE = Path("dados/bronze/gym_members")


def baixar():
    """Baixa o dataset do Kaggle e retorna o caminho local onde ele foi salvo."""
    pasta = kagglehub.dataset_download(DATASET)
    print("baixado em:", pasta)
    return Path(pasta)


def localizar(pasta):
    """Procura o arquivo CSV na pasta baixada, sem depender do nome exato."""
    arquivos = list(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError("nenhum CSV encontrado na pasta baixada")
    print("encontrados:", [a.name for a in arquivos])
    return arquivos[0]


def copiar(origem):
    """Copia o arquivo para a camada bronze, com a data de extração no nome."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"gym_members_exercise_tracking_{hoje}.csv"
    shutil.copy(origem, destino)
    return destino


def registrar(origem, destino):
    """Grava o arquivo de proveniência: de onde veio, quando e qual arquivo original."""
    info = {
        "fonte": DATASET,
        "arquivo_origem": origem.name,
        "arquivo_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
    }
    (BRONZE / "proveniencia.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False)
    )


def main():
    pasta = baixar()
    origem = localizar(pasta)
    destino = copiar(origem)
    registrar(origem, destino)
    print("concluido:", destino)


if __name__ == "__main__":
    main()