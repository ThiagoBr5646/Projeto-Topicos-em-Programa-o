"""Transforma a Bronze do Compendio de Atividades Fisicas na Prata.

Aula 7 - Enriquecimento: juntar fontes (ECOX14).

O Compendio e o cadastro desta juncao: uma linha por atividade fisica,
com o codigo da atividade e o gasto de energia dela em MET (1 MET e o
gasto em repouso, cerca de 1 kcal por kg de peso por hora). A academia
diz QUAL treino foi feito; o Compendio diz QUANTO esse treino costuma
gastar. As duas informacoes ja existiam, so que separadas.

Por que o dado vem separado: o Compendio muda a cada dez anos e mais
(1993, 2000, 2011, 2024); a sessao de academia nasce a cada treino.
Guardar o MET dentro de cada sessao obrigaria a reescrever todas elas
quando o Compendio fosse atualizado.

Como executar, a partir da raiz do projeto:
    python src/transformar_compendio.py
"""
from datetime import datetime
from pathlib import Path
import json

import pandas as pd

import juncao    # modulo do projeto, em src/
import limpeza   # modulo do projeto, em src/

BRONZE = Path("dados/bronze/compendio")
PRATA = Path("dados/prata")
PADRAO = "compendio_condicionamento_*.csv"

# Nomes da fonte (em ingles, como estao na pagina) -> nomes da prata.
COLUNAS = {
    "Specific Activity Code": "codigo",
    "MET Value": "met",
    "Activity Description": "atividade_compendio",
}

# Faixa plausivel de MET para adulto: do repouso sentado (~1) ao
# esforco maximo de atleta (~23 no Compendio inteiro).
FAIXA_MET = (0.9, 25.0)


def carregar():
    """Le o arquivo mais recente da bronze (a data no nome ordena).

    O codigo tem zero a esquerda ('02000'). Lido como numero ele vira
    2000 e nunca mais casa com o texto '02000': e o motivo "tipo
    diferente" da aula. Por isso ele e lido como texto desde o inicio,
    e nao convertido depois.
    """
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho, dtype={"Specific Activity Code": "string"})
    print("lido:", caminho.name, df.shape)
    return df, caminho


def codigos_estimados():
    """Le, da proveniencia da bronze, a lista de MET que a propria fonte
    marca como estimados (em vermelho na pagina)."""
    info = json.loads((BRONZE / "proveniencia.json").read_text(encoding="utf-8"))
    return info.get("valores_estimados_na_fonte", [])


def padronizar(df):
    """Renomeia, tira espacos e da tipo a cada coluna."""
    df = df.rename(columns=COLUNAS)
    df = limpeza.tirar_espacos(df)
    df["codigo"] = df["codigo"].astype("string")
    df["met"] = pd.to_numeric(df["met"], errors="coerce")
    df["atividade_compendio"] = df["atividade_compendio"].astype("string")
    return df


def conferir_codigo(df):
    """O codigo do Compendio tem sempre 5 digitos. Fora disso e defeito
    de leitura (o zero a esquerda sumiu, por exemplo)."""
    fora_do_formato = int((~df["codigo"].str.fullmatch(r"\d{5}")).sum())
    print("codigos fora do formato de 5 digitos:", fora_do_formato)
    ausentes, repetidos = juncao.conferir_chave(df, "codigo")
    return fora_do_formato, ausentes, repetidos


def conferir_met(df):
    """MET ausente ou fora da faixa plausivel e sinalizado, nao removido."""
    sem_met = int(df["met"].isna().sum())
    fora = df["met"].notna() & ~df["met"].between(*FAIXA_MET)
    print("MET ausente:", sem_met, "| fora de", FAIXA_MET, ":", int(fora.sum()))
    print(df["met"].describe().round(2).to_dict())
    return sem_met, int(fora.sum())


def marcar_estimados(df):
    """Cria met_estimado: True quando a fonte avisa que o valor nao tem
    estudo publicado por tras. Quem usar o MET precisa saber disso."""
    estimados = codigos_estimados()
    df["met_estimado"] = df["codigo"].isin(estimados)
    print("MET estimados pela fonte:", int(df["met_estimado"].sum()))
    return df


def salvar(df):
    """Grava a prata em Parquet (guarda o tipo texto do codigo)."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "compendio.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    """Registra a proveniencia: uma linha por execucao, no fim do arquivo."""
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

    df = padronizar(df)
    fora_do_formato, ausentes, repetidos = conferir_codigo(df)
    sem_met, met_fora = conferir_met(df)
    df = marcar_estimados(df)

    depois = len(df)
    destino = salvar(df)

    decisoes = [
        "Codigo lido como texto (dtype string) direto do CSV: tem zero a "
        "esquerda, e como numero deixaria de casar com a academia.",
        f"Codigos fora do formato de 5 digitos: {fora_do_formato}; "
        f"ausentes: {ausentes}; repetidos: {repetidos}. Chave unica: o "
        "cadastro pode ser o lado 'one' de uma juncao many_to_one.",
        f"MET convertido para numero; ausentes: {sem_met}; fora da faixa "
        f"{FAIXA_MET}: {met_fora} (sinalizados, nao removidos).",
        "met_estimado = True nos codigos que a propria fonte marca como "
        "estimados (lista na proveniencia da bronze).",
        "Colunas renomeadas: codigo, met, atividade_compendio. A descricao "
        "fica em ingles, como na fonte.",
    ]
    info = registrar(origem, destino, antes, depois, decisoes)

    print("concluido:", destino)
    print("linhas: antes =", antes, "| depois =", depois)
    return info


if __name__ == "__main__":
    main()
