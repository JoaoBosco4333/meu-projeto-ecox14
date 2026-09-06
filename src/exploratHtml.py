from pathlib import Path
import sys
import pandas as pd
from data_profiling import ProfileReport

BRONZE = Path("dados/bronze")
RELATORIOS = Path("relatorios")

FONTES = {
    "sim": BRONZE / "SIM_2024.csv",
    "sinasc": BRONZE / "SINASC_2024.csv",
}

def carregar(fonte):
    caminho = FONTES[fonte]
    return pd.read_csv(caminho, sep=";", encoding="latin-1", low_memory=False)

def gerar(fonte):
    df = carregar(fonte)
    perfil = ProfileReport(df, title=fonte.upper(), minimal=True)
    RELATORIOS.mkdir(exist_ok=True)
    saida = RELATORIOS / f"{fonte}.html"
    perfil.to_file(saida)
    return saida

def main(fonte):
    print("perfilando:", fonte)
    print(gerar(fonte))

if __name__ == "__main__":
    fonte = sys.argv[1] if len(sys.argv) > 1 else "sim"
    main(fonte)