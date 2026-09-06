from pathlib import Path

caminho = Path(r"C:\Users\joaob\Documents\Topicos Especiais em Prog\PROJETO ENGENHARIA DE DADOS\meu-projeto\dados\bronze\SINASC_2024.csv")

with open(caminho, "rb") as f:
    for _ in range(3):
        print(f.readline())