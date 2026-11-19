"""Roda o dbt pelo python.exe, sem o dbt.exe.

Por que existe: no Windows com Controle de Aplicativo (Smart App Control)
ligado, os .exe que o pip cria na .venv (pip.exe, dbt.exe, streamlit.exe)
nao tem assinatura digital e sao bloqueados. O python.exe e assinado e
roda. O dbt nao aceita 'python -m dbt', entao este arquivo chama o mesmo
ponto de entrada que o dbt.exe chamaria.

Uso, de qualquer pasta (com a .venv ativada):
    python ecox14/rodar_dbt.py build
    python ecox14/rodar_dbt.py docs generate
    python ecox14/rodar_dbt.py docs serve
    python ecox14/rodar_dbt.py debug
"""
from pathlib import Path
import os

from dbt.cli.main import cli

# O dbt procura o dbt_project.yml e o profiles.yml na pasta atual, e o
# caminho do banco no profiles.yml e relativo a ela: sempre ecox14/.
os.chdir(Path(__file__).resolve().parent)

if __name__ == "__main__":
    cli()
