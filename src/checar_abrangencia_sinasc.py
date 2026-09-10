from pathlib import Path
import pandas as pd

CAMINHO = Path("dados/bronze/SINASC_2024.csv")

df = pd.read_csv(
    CAMINHO,
    sep=";",
    encoding="latin-1",
    usecols=["CODMUNRES", "DTNASC"],
    low_memory=False,
)

print("linhas:", len(df))
print("municipios distintos (CODMUNRES):", df["CODMUNRES"].nunique())

datas = pd.to_datetime(df["DTNASC"], format="%d%m%Y", errors="coerce")
print("data mais antiga:", datas.min())
print("data mais recente:", datas.max())
print("anos presentes:", sorted(datas.dt.year.dropna().unique()))