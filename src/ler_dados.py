import pandas as pd

CAMINHO = "./meu-projeto/dados/bronze/SIM_2024.csv"

df = pd.read_csv(CAMINHO, sep=';')

print(df.shape)
#print(df.head())
#print(df.columns)

#for coluna in df.columns:
#    print(f"{coluna}: {df[coluna].dtype}")