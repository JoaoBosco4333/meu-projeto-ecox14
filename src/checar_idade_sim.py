import pandas as pd

df = pd.read_parquet("dados/prata/sim.parquet")

print(df["idade_anos"].describe())
print()
print("extremos IQR - resumo da idade:")
print(df[df["idade_anos_extremo"]]["idade_anos"].describe())
print()
print("quantos extremos tem idade_anos == 0 (menor de 1 ano):")
print((df.loc[df["idade_anos_extremo"], "idade_anos"] == 0).sum())
print()
print("quantos extremos tem idade_anos >= 90:")
print((df.loc[df["idade_anos_extremo"], "idade_anos"] >= 90).sum())