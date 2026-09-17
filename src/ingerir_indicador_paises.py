"""
Ingestao da terceira fonte: indicador por pais e por ano.

O nome diz o que o arquivo traz: um indicador, medido por pais,
ao longo do tempo. Compare com ingerir_paises.py, que traz o
cadastro dos paises, sem tempo nenhum. Sao duas fontes da mesma
origem e de naturezas diferentes, e o nome precisa separar as
duas.

Banco Mundial tem milhares de series. Alguns exemplos:
    SP.POP.TOTL        populacao total
    NY.GDP.PCAP.CD     PIB per capita em dolares
    SE.XPD.TOTL.GD.ZS  gasto publico em educacao, % do PIB
    EN.ATM.CO2E.PC     emissao de CO2 per capita
    SH.XPD.CHEX.PC.CD  gasto corrente em saude per capita, em dolares

A serie escolhida neste projeto e a ultima da lista: gasto em saude
per capita. O tema do projeto e treino em academia, e o gasto em
saude e a variavel de contexto mais proxima disso entre as series
disponiveis.

Como executar, a partir da raiz do projeto:
    python src/ingerir_indicador_paises.py
"""

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

INDICADOR = "SH.XPD.CHEX.PC.CD"
PERIODO = "2000:2023"
POR_PAGINA = 1000

URL = f"https://api.worldbank.org/v2/country/all/indicator/{INDICADOR}"

# A bronze tem dois niveis: origem, depois conjunto de dados.
# A origem e o sistema de onde o dado vem. O conjunto e a tabela
# em si, com o proprio esquema e a propria granularidade.
BRONZE = Path("dados/bronze/banco_mundial/indicador_paises")


def buscar_pagina(pagina):
    """Busca uma pagina e devolve (metadados, registros)."""
    resposta = requests.get(
        URL,
        params={
            "format": "json",
            "date": PERIODO,
            "per_page": POR_PAGINA,
            "page": pagina,
        },
        timeout=60,
    )
    resposta.raise_for_status()
    dados = resposta.json()
    return dados[0], dados[1]


def buscar_tudo():
    """Percorre todas as paginas ate nao faltar nenhuma.

    Este e o laco que a aula de ingestao anunciou e nao escreveu.
    A primeira chamada serve para descobrir quantas paginas
    existem; as seguintes buscam o que falta.
    """
    meta, registros = buscar_pagina(1)
    total_paginas = meta["pages"]
    print("total de registros informados:", meta["total"])
    print("paginas                      :", total_paginas)
    print("atualizado pela fonte em     :", meta.get("lastupdated"))

    for pagina in range(2, total_paginas + 1):
        print(f"  buscando pagina {pagina} de {total_paginas}")
        _, mais = buscar_pagina(pagina)
        registros.extend(mais)

    print("registros recebidos          :", len(registros))
    if len(registros) != meta["total"]:
        print("ATENCAO: recebido diferente do informado pela API.")
    return meta, registros


def salvar(registros):
    """Achata o JSON aninhado e grava na bronze com a data no nome."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    df = pd.json_normalize(registros)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"{INDICADOR}_{hoje}.csv"
    df.to_csv(destino, index=False)

    print()
    print("formato:", df.shape)
    print("colunas:", df.columns.tolist())
    print("salvo em:", destino)
    return destino


def registrar(destino, meta, quantidade):
    """Proveniencia, agora com a data de atualizacao da fonte.

    O lastupdated responde a pergunta de atualidade: o dado ainda
    vale? Guardar isso no momento da coleta e o que permite
    responder depois, sem ter que consultar a API de novo.
    """
    info = {
        "fonte": URL,
        "indicador": INDICADOR,
        "periodo": PERIODO,
        "arquivo_bronze": destino.name,
        "registros_informados_pela_api": meta["total"],
        "registros_recebidos": quantidade,
        "fonte_atualizada_em": meta.get("lastupdated"),
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = BRONZE / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    print("proveniencia:", caminho)
    return info


def main():
    meta, registros = buscar_tudo()
    destino = salvar(registros)
    registrar(destino, meta, len(registros))


if __name__ == "__main__":
    main()