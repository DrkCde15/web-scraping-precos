"""Modulo de analise de dados de precos."""

import json
import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)


def load_data(filepath: str = "data/produtos.csv") -> pd.DataFrame:
    """Carrega dados de produtos de um CSV ou JSON."""
    path = Path(filepath)

    if path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    else:
        df = pd.read_csv(filepath)

    df["preco"] = pd.to_numeric(df["preco"], errors="coerce")
    df.dropna(subset=["preco"], inplace=True)
    return df


def load_from_db(
    db_path: str = "data/produtos.db",
    fonte: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> pd.DataFrame:
    """Carrega dados diretamente do banco SQLite."""
    from src.db import DatabaseManager

    db = DatabaseManager(db_path=db_path)
    records = db.query_filtered(fonte=fonte, min_price=min_price, max_price=max_price)
    if not records:
        return pd.DataFrame(columns=["nome", "preco", "url", "fonte", "data_coleta"])
    return pd.DataFrame(records)


def calc_stats(df: pd.DataFrame) -> dict[str, float]:
    return {
        "media": df["preco"].mean(),
        "mediana": df["preco"].median(),
        "desvio_padrao": df["preco"].std(),
        "minimo": df["preco"].min(),
        "maximo": df["preco"].max(),
        "qtd_produtos": len(df),
    }


def plot_price_distribution(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    sns.histplot(data=df, x="preco", bins=20, kde=True, ax=axes[0])
    axes[0].set_title("Distribuicao de Precos")
    axes[0].set_xlabel("Preco")
    axes[0].set_ylabel("Frequencia")

    sns.boxplot(data=df, y="preco", ax=axes[1])
    axes[1].set_title("Boxplot de Precos")
    axes[1].set_ylabel("Preco")

    plt.tight_layout()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info("Grafico salvo em %s", output_path)

    plt.close(fig)


def compare_prices(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    mais_baratos = df.nsmallest(top_n, "preco").copy()
    mais_baratos["categoria"] = "Mais Barato"

    mais_caros = df.nlargest(top_n, "preco").copy()
    mais_caros["categoria"] = "Mais Caro"

    return pd.concat([mais_baratos, mais_caros], ignore_index=True)


def compare_sources(df: pd.DataFrame) -> pd.DataFrame:
    """Compara estatisticas de precos entre diferentes fontes/sites."""
    if "fonte" not in df.columns or df["fonte"].isna().all():
        logger.warning("Dados sem informacao de fonte para comparacao cross-site")
        return pd.DataFrame()

    stats_por_fonte = df.groupby("fonte")["preco"].agg(
        media="mean",
        mediana="median",
        desvio="std",
        minimo="min",
        maximo="max",
        qtd="count",
    ).round(2)

    return stats_por_fonte.reset_index()


def summary_report(df: pd.DataFrame, output_path: str = "data/relatorio.txt") -> str:
    stats = calc_stats(df)

    relatorio = (
        f"=== RELATORIO DE PRECOS ===\n\n"
        f"Total de produtos: {stats['qtd_produtos']}\n"
        f"Preco medio: {stats['media']:.2f}\n"
        f"Preco mediano: {stats['mediana']:.2f}\n"
        f"Desvio padrao: {stats['desvio_padrao']:.2f}\n"
        f"Preco minimo: {stats['minimo']:.2f}\n"
        f"Preco maximo: {stats['maximo']:.2f}\n"
    )

    if "fonte" in df.columns and not df["fonte"].isna().all():
        relatorio += "\n=== POR FONTE ===\n"
        for fonte, grupo in df.groupby("fonte"):
            s = calc_stats(grupo)
            relatorio += (
                f"\n  {fonte}:\n"
                f"    Produtos: {s['qtd_produtos']}\n"
                f"    Media: {s['media']:.2f}\n"
                f"    Min: {s['minimo']:.2f} | Max: {s['maximo']:.2f}\n"
            )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(relatorio)

    logger.info("Relatorio gerado em %s", output_path)
    return relatorio
