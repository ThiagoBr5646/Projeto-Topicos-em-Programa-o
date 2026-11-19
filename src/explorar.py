"""Gera o relatorio de perfilamento da base da academia (aula 4).

Nao faz parte do pipeline: e exploracao, roda quando alguem quer olhar
a base de novo. O relatorio (16 MB) fica em relatorios/, fora do git.

Como executar, de qualquer pasta:
    python src/explorar.py
"""
from pathlib import Path
import logging

import pandas as pd

from config import BRONZE_ACADEMIA, PADRAO_ACADEMIA, RELATORIOS

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)


def mais_recente():
    """Retorna o arquivo mais novo da bronze, assumindo nomes com data
    no formato ano-mes-dia (ordem alfabetica = ordem cronologica)."""
    arquivos = sorted(BRONZE_ACADEMIA.glob(PADRAO_ACADEMIA))
    if not arquivos:
        raise FileNotFoundError(f"bronze vazia: {BRONZE_ACADEMIA}")
    return arquivos[-1]


def gerar(caminho):
    """Le o CSV e gera o relatorio de profiling em HTML."""
    from data_profiling import ProfileReport  # pesado: so quando precisa
    df = pd.read_csv(caminho)
    perfil = ProfileReport(df, title=caminho.name)
    RELATORIOS.mkdir(exist_ok=True)
    saida = RELATORIOS / f"{caminho.stem}.html"
    perfil.to_file(saida)
    return saida


def main():
    caminho = mais_recente()
    log.info("perfilando: %s", caminho.name)
    log.info("relatorio: %s", gerar(caminho))


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()
