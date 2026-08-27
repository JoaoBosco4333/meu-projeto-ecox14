from pathlib import Path
from datetime import date
from datetime import datetime
import shutil
import kagglehub
import json

DATASET = "rishavsvault/most-streamed-artists-on-spotify"
BRONZE = Path("dados/bronze/spotify")


def baixar():
    pasta = kagglehub.dataset_download(DATASET)
    print("Baixado em:", pasta)
    return Path(pasta)


def localizar(pasta):
    arquivos = list(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError("Nenhum CSV encontrado")
    print("Encontrados:", [a.name for a in arquivos])
    return arquivos[0]


def copiar(origem):
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"artists_{hoje}.csv"
    shutil.copy(origem, destino)
    return destino

def registrar(origem, destino):
    info = {
        "fonte": DATASET,
        "arquivo_origem": origem.name,
        "arquivo_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
    }
    caminho = BRONZE / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(info, ensure_ascii=False)
            + "\n")


def main():
    pasta = baixar()
    origem = localizar(pasta)
    destino = copiar(origem)
    print("Copiado para:", destino)
    registrar(origem, destino)

if __name__ == "__main__":
    main()