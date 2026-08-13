import pandas as pd

CAMINHO = "./dados/bronze/Spotify.csv"

df = pd.read_csv(CAMINHO)

print(df.shape)
print(df.head())
print(df.columns)

for coluna in df.columns:
    print(f"{coluna}: {df[coluna].dtype}")