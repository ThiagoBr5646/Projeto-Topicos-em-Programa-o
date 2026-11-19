"""Ingestao: baixa a base da academia do Kaggle e guarda na bronze.

Aula 3 (ingestao) e Aula 8 (pipeline) - ECOX14.

O Compendio de Atividades Fisicas nao tem ingestao automatica: a pagina
e publica, mas nao tem API nem arquivo para baixar, e a tabela foi
copiada para CSV a mao (README, "Fontes de dados"). Esta etapa so
confere que o arquivo dele esta na bronze.

Como executar, de qualquer pasta:
    python src/pipeline.py              (o pipeline inteiro)
    python src/ingerir.py               (so esta etapa)
O token do Kaggle precisa estar configurado (kaggle.json, fora do git).
"""
from datetime import date, datetime
from pathlib import Path
import json
import logging
import shutil

from config import (BRONZE_ACADEMIA, BRONZE_COMPENDIO, DATASET_KAGGLE,
                    PADRAO_ACADEMIA, PADRAO_COMPENDIO)

# Nome do arquivo, e nao __name__: rodado direto, __name__ seria "__main__"
# e o log nao diria de qual modulo veio a mensagem.
log = logging.getLogger(Path(__file__).stem)


def baixar():
    """Baixa o dataset do Kaggle e retorna a pasta local onde ele ficou.

    O import fica aqui dentro: quem so quer rodar a transformacao nao
    precisa do kagglehub instalado para importar este modulo.
    """
    import kagglehub
    pasta = kagglehub.dataset_download(DATASET_KAGGLE)
    log.debug("baixado em: %s", pasta)
    return Path(pasta)


def localizar(pasta):
    """Procura o arquivo CSV na pasta baixada, sem depender do nome exato."""
    arquivos = list(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"nenhum CSV encontrado em {pasta}")
    log.debug("encontrados: %s", [a.name for a in arquivos])
    return arquivos[0]


def copiar(origem):
    """Copia o arquivo para a bronze, com a data de extracao no nome."""
    BRONZE_ACADEMIA.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE_ACADEMIA / f"gym_members_exercise_tracking_{hoje}.csv"
    shutil.copy(origem, destino)
    return destino


def registrar(origem, destino):
    """Grava a proveniencia: de onde veio, quando e qual o arquivo original."""
    info = {
        "fonte": DATASET_KAGGLE,
        "arquivo_origem": origem.name,
        "arquivo_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
    }
    (BRONZE_ACADEMIA / "proveniencia.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def ingerir_academia():
    """Baixa a academia do Kaggle. Se o download falhar, TRATA E DECIDE.

    A bronze guarda cada extracao com a data no nome, entao uma falha
    de rede ou de token nao apaga nada: a extracao anterior continua la.
    Decisao: se ja existe uma extracao, o pipeline segue com ela e
    deixa um WARNING dizendo qual arquivo usou - nao engole o erro. Se
    a bronze esta vazia, nao ha com o que seguir: o erro sobe.
    """
    try:
        origem = localizar(baixar())
    except Exception as erro:
        anteriores = sorted(BRONZE_ACADEMIA.glob(PADRAO_ACADEMIA))
        if not anteriores:
            log.error("academia: download falhou e a bronze esta vazia")
            raise
        log.warning("academia: download falhou (%s: %s); seguindo com a "
                    "extracao anterior %s", type(erro).__name__, erro,
                    anteriores[-1].name)
        return anteriores[-1]

    destino = copiar(origem)
    registrar(origem, destino)
    with destino.open(encoding="utf-8") as f:
        linhas = sum(1 for _ in f) - 1
    log.info("academia: %s, %d registros", destino.name, linhas)
    return destino


def conferir_compendio():
    """O Compendio nao e baixado: so confere que a copia esta na bronze."""
    arquivos = sorted(BRONZE_COMPENDIO.glob(PADRAO_COMPENDIO))
    if not arquivos:
        raise FileNotFoundError(
            f"Compendio ausente em {BRONZE_COMPENDIO}: ele e copiado a mao, "
            "veja o README")
    log.info("compendio: sem ingestao automatica, usando %s", arquivos[-1].name)
    return arquivos[-1]


def ingerir_todas():
    """Etapa 'ingestao' do pipeline: todas as fontes, uma apos a outra."""
    ingerir_academia()
    conferir_compendio()


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    ingerir_todas()
