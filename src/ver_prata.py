import pandas as pd

pd.set_option("display.max_columns", 15)
pd.set_option("display.width", 150)

sim = pd.read_parquet("dados/prata/sim.parquet")
sinasc = pd.read_parquet("dados/prata/sinasc.parquet")

print("=== SIM: 5 linhas, colunas escolhidas ===")
print(sim[["contador", "IDADE", "idade_anos", "DTOBITO", "idade_anos_extremo"]].head())

print()
print("=== SINASC: 5 linhas, colunas escolhidas ===")
print(sinasc[["contador", "PESO", "PESO_extremo", "APGAR1", "DTNASC"]].head())