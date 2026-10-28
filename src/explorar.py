import sys
from pathlib import Path
import pandas as pd
from ydata_profiling import ProfileReport  

# --- Definição de Caminhos e Estrutura de Pastas ---
# Define os caminhos base usando a biblioteca Pathlib (independente de SO)
BRONZE = Path("dados/bronze")
RELATORIOS = Path("relatorios")

# Mapeia as chaves das fontes aos seus respectivos arquivos de dados brutos
FONTES = {
    "sim": BRONZE / "SIM_2024.csv",
    "sinasc": BRONZE / "SINASC_2024.csv",
}


def carregar(fonte):
    """Carrega o arquivo CSV da fonte especificada em um DataFrame Pandas.

    Usa separador ';' e codificação 'latin-1' (padrão de arquivos DataSUS).
    """
    caminho = FONTES[fonte]
    # low_memory=False evita avisos de tipos mistos em arquivos grandes
    return pd.read_csv(caminho, sep=";", encoding="latin-1", low_memory=False)


def gerar(fonte):
    """Gera um relatório profilador completo em formato HTML para a fonte escolhida."""
    df = carregar(fonte)

    # minimal=True acelera a geração desativando gráficos pesados (como correlações detalhadas)
    perfil = ProfileReport(df, title=fonte.upper(), minimal=True)

    # Garante que a pasta de destino exista antes de salvar
    RELATORIOS.mkdir(exist_ok=True)

    saida = RELATORIOS / f"{fonte}.html"
    perfil.to_file(saida)
    return saida


def alertas(fonte):
    """Extrai os alertas de qualidade de dados gerados pelo Profiling (ex: valores ausentes,

    constantes, alta cardinalidade) e salva em um arquivo de texto limpo.
    """
    df = carregar(fonte)
    perfil = ProfileReport(df, title=fonte.upper(), minimal=True)

    # Obtém o dicionário interno/objeto de métricas do relatório
    descricao = perfil.get_description()

    # Cria a pasta de relatórios caso ela não exista
    RELATORIOS.mkdir(exist_ok=True)
    saida = RELATORIOS / f"{fonte}_alertas.txt"

    with open(saida, "w", encoding="utf-8") as f:
        # Percorre cada alerta identificado no perfilamento do dataset
        for alerta in descricao.alerts:
            # Garante a extração do tipo de alerta mesmo em versões diferentes da biblioteca
            tipo = getattr(alerta, "alert_type_name", None) or getattr(
                alerta, "alert_type", ""
            )
            coluna = getattr(alerta, "column_name", "") or "(dataset)"

            # Grava no formato: TIPO | COLUNA | MENSAGEM
            f.write(f"{tipo} | {coluna} | {alerta}\n")

    print("alertas salvos em:", saida)
    return saida


def main(fonte):
    """Ponto de entrada para geração do relatório HTML completo."""
    print("perfilando:", fonte)
    print(gerar(fonte))


if __name__ == "__main__":
    fonte = sys.argv[1] if len(sys.argv) > 1 else "sim"

    # Executa a extração de alertas
    alertas(fonte)