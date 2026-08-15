import pandas as pd

CAMINHO = "dados/bronze/gym_members_exercise_tracking.csv"
df = pd.read_csv(CAMINHO)
print(df.shape)