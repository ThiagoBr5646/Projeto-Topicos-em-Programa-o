from pathlib import Path

import pandas as pd

# Lê o CSV mais recente da bronze da academia, o mesmo que os outros scripts usam.
# A data no nome (AAAAMMDD) faz a ordem alfabética ser a ordem cronológica.
BRONZE = Path("dados/bronze/gym_members")
PADRAO = "gym_members_exercise_tracking_*.csv"

arquivos = sorted(BRONZE.glob(PADRAO))
if not arquivos:
    raise FileNotFoundError(f"nada em {BRONZE}")

caminho = arquivos[-1]
df = pd.read_csv(caminho)
print(caminho.name, df.shape)
