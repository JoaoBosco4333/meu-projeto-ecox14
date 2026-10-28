import pandas as pd

UF = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
      21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
      28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
      42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}

for nome, arquivo in [("SIM", "sim_enriquecido"), ("SINASC", "sinasc_enriquecido")]:
    df = pd.read_parquet(f"dados/prata/{arquivo}.parquet",
                         columns=["CODMUNRES", "codigo_municipio_6"])
    sem_par = df[df["codigo_municipio_6"].isna()]
    por_codigo = sem_par["CODMUNRES"].value_counts().rename("linhas").reset_index()
    por_codigo["formato_UF0000"] = por_codigo["CODMUNRES"] % 10000 == 0
    por_codigo["uf"] = (por_codigo["CODMUNRES"] // 10000).map(UF)

    padrao = por_codigo[por_codigo["formato_UF0000"]]
    fora = por_codigo[~por_codigo["formato_UF0000"]]

    print(f"\n=== {nome}: {len(sem_par):,} linhas sem par, {len(por_codigo)} codigos ===")
    print("codigos no formato UF+0000:", len(padrao), "| linhas:", int(padrao["linhas"].sum()))
    print("codigos FORA desse formato:", len(fora), "| linhas:", int(fora["linhas"].sum()))
    print(por_codigo.to_string(index=False))