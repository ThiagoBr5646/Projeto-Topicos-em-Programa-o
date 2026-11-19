"""Ponto de entrada do pipeline: roda todas as etapas, na ordem.

Aula 8 - De scripts soltos a pipeline (ECOX14).
Aula 9 - a etapa carga deixou de ser None.
Aula 10 - a etapa modelagem deixou de ser None: o pipeline esta completo.

A ordem que antes existia so na cabeca de quem escreveu agora esta
escrita em ETAPAS. Cada etapa loga inicio, fim e quanto tempo levou; se
uma falhar, o erro vai inteiro para o log e o pipeline PARA - seguir
para a etapa seguinte com dado pela metade seria mentir que deu certo.

Como executar, de qualquer pasta:
    python src/pipeline.py                  tudo, desde o Kaggle
    python src/pipeline.py transformacao    retoma desta etapa em diante
    python src/pipeline.py modelagem        so o dbt (Ouro e testes)

Regra de dependencia: este arquivo importa as etapas; nenhuma etapa
importa o pipeline. Os imports das etapas ficam dentro das funcoes:
erro de import em uma etapa nao impede as outras de rodar.
"""
import logging
import re
import subprocess
import sys
import time

import config

log = logging.getLogger("pipeline")


def etapa_ingestao():
    import ingerir
    ingerir.ingerir_todas()


def etapa_transformacao():
    import transformar_gym_members
    import transformar_compendio
    transformar_gym_members.main()
    transformar_compendio.main()


def etapa_enriquecimento():
    import enriquecer_gym_members
    enriquecer_gym_members.main()


def etapa_carga():
    import carga
    carga.main()


def etapa_modelagem():
    """Aula 10/11: o dbt constroi a Ouro e testa o resultado.

    'dbt build' = run + test, na ordem do grafo: testa as origens,
    constroi cada modelo e testa logo em seguida. Se um teste falha, os
    modelos que dependem dele nem sao construidos.

    A saida do dbt passa linha a linha pelo log, para o resultado dos
    testes ficar no pipeline.log junto com o resto. Se o dbt terminar
    com erro, o Python levanta erro (o mesmo que check=True faz) - sem
    isso, o pipeline diria que terminou bem com a Ouro quebrada.
    """
    # O dbt roda pelo python.exe da .venv (ecox14/rodar_dbt.py), e nao pelo
    # dbt.exe: o Controle de Aplicativo do Windows bloqueia os .exe sem
    # assinatura que o pip cria. sys.executable e o Python que esta rodando.
    comando = [sys.executable, str(config.DBT / "rodar_dbt.py"),
               "--no-use-colors", "build"]
    dbt_log = logging.getLogger("dbt")
    with subprocess.Popen(comando, cwd=config.DBT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace") as processo:
        for linha in processo.stdout:
            # o dbt carimba a propria hora; o log ja carimba a dele
            linha = re.sub(r"^\d\d:\d\d:\d\d\s*", "", linha.rstrip())
            if linha:
                dbt_log.info(linha)
    if processo.returncode != 0:
        raise subprocess.CalledProcessError(processo.returncode, comando)


ETAPAS = [
    ("ingestao", etapa_ingestao),
    ("transformacao", etapa_transformacao),
    ("enriquecimento", etapa_enriquecimento),
    ("carga", etapa_carga),            # aula 9: era None
    ("modelagem", etapa_modelagem),    # aula 10: era None
]


def executar(nome, funcao):
    """Roda uma etapa: loga inicio e fim; se falhar, loga o rastro e para."""
    log.info("etapa %s: inicio", nome)
    comeco = time.perf_counter()
    try:
        funcao()
    except Exception:
        # log.exception grava a mensagem e o rastro inteiro, com a linha
        # exata. O raise devolve o erro para cima: o pipeline para aqui.
        log.exception("etapa %s falhou", nome)
        raise
    log.info("etapa %s: fim em %.0fs", nome, time.perf_counter() - comeco)


def main(a_partir_de=None):
    config.configurar_log()
    nomes = [nome for nome, _ in ETAPAS]
    if a_partir_de is not None and a_partir_de not in nomes:
        log.error("etapa desconhecida: %r. Etapas: %s",
                  a_partir_de, ", ".join(nomes))
        sys.exit(2)

    comecou = a_partir_de is None
    for nome, funcao in ETAPAS:
        if nome == a_partir_de:
            comecou = True
        if not comecou or funcao is None:
            log.info("etapa %s: pulada", nome)
            continue
        executar(nome, funcao)
    log.info("pipeline concluido")


if __name__ == "__main__":
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception:
        sys.exit(1)  # o rastro ja foi para o log em executar()
