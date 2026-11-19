"""Leitura rapida da bronze: abre o CSV mais recente e mostra o formato.

Nao faz parte do pipeline. A data no nome (AAAAMMDD) faz a ordem
alfabetica ser a ordem cronologica.

Como executar, de qualquer pasta:
    python src/ler_dados.py
"""
from pathlib import Path
import logging

import pandas as pd

from config import BRONZE_ACADEMIA, PADRAO_ACADEMIA

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)


def main():
    arquivos = sorted(BRONZE_ACADEMIA.glob(PADRAO_ACADEMIA))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE_ACADEMIA}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    log.info("%s %s", caminho.name, df.shape)
    return df


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()
