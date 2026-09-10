import pandas as pd

df = pd.read_parquet("dados/prata/sinasc.parquet")

print(df["PESO"].describe())
print()
extremos = df.loc[df["PESO_extremo"], "PESO"]
print("extremos - resumo do peso:")
print(extremos.describe())
print()
print("extremos abaixo de 2500g (baixo peso):", (extremos < 2500).sum())
print("extremos acima de 4000g (alto peso):", (extremos > 4000).sum())