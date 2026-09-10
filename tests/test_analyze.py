"""Testes para o modulo de analise de dados."""

import json
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

from src.analyze import (
    calc_stats,
    compare_prices,
    compare_sources,
    load_data,
    plot_price_distribution,
    summary_report,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nome": ["Produto A", "Produto B", "Produto C", "Produto D", "Produto E"],
            "preco": [100.0, 250.0, 50.0, 500.0, 150.0],
            "url": [
                "http://a.com",
                "http://b.com",
                "http://c.com",
                "http://d.com",
                "http://e.com",
            ],
            "fonte": ["site1", "site1", "site2", "site2", "site1"],
        }
    )


@pytest.fixture
def csv_file(tmp_path: Path, sample_df: pd.DataFrame) -> str:
    filepath = str(tmp_path / "test_produtos.csv")
    sample_df.to_csv(filepath, index=False)
    return filepath


@pytest.fixture
def json_file(tmp_path: Path, sample_df: pd.DataFrame) -> str:
    filepath = str(tmp_path / "test_produtos.json")
    data = sample_df.to_dict(orient="records")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return filepath


class TestLoadData:
    def test_load_data_csv(self, csv_file: str) -> None:
        df = load_data(csv_file)
        assert len(df) == 5
        assert list(df.columns)[:3] == ["nome", "preco", "url"]

    def test_load_data_json(self, json_file: str) -> None:
        df = load_data(json_file)
        assert len(df) == 5
        assert "preco" in df.columns

    def test_load_data_coluna_preco_numerica(self, csv_file: str) -> None:
        df = load_data(csv_file)
        assert pd.api.types.is_numeric_dtype(df["preco"])

    def test_load_data_arquivo_inexistente(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_data("arquivo_inexistente.csv")


class TestCalcStats:
    def test_calc_stats_valores(self, sample_df: pd.DataFrame) -> None:
        stats = calc_stats(sample_df)
        assert stats["qtd_produtos"] == 5
        assert stats["minimo"] == 50.0
        assert stats["maximo"] == 500.0
        assert stats["media"] == pytest.approx(210.0)
        assert stats["mediana"] == 150.0

    def test_calc_stats_chaves(self, sample_df: pd.DataFrame) -> None:
        stats = calc_stats(sample_df)
        expected_keys = {"media", "mediana", "desvio_padrao", "minimo", "maximo", "qtd_produtos"}
        assert set(stats.keys()) == expected_keys


class TestPlotPriceDistribution:
    def test_plot_nao_levanta_excecao(self, sample_df: pd.DataFrame) -> None:
        plot_price_distribution(sample_df)

    def test_plot_salva_arquivo(self, sample_df: pd.DataFrame, tmp_path: Path) -> None:
        output_path = str(tmp_path / "grafico.png")
        plot_price_distribution(sample_df, output_path=output_path)
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0


class TestComparePrices:
    def test_compare_prices_top_n(self, sample_df: pd.DataFrame) -> None:
        result = compare_prices(sample_df, top_n=2)
        assert len(result) == 4

    def test_compare_prices_categorias(self, sample_df: pd.DataFrame) -> None:
        result = compare_prices(sample_df, top_n=2)
        assert set(result["categoria"].unique()) == {"Mais Barato", "Mais Caro"}


class TestCompareSources:
    def test_compare_sources(self, sample_df: pd.DataFrame) -> None:
        result = compare_sources(sample_df)
        assert not result.empty
        assert "fonte" in result.columns
        assert "media" in result.columns
        assert len(result) == 2

    def test_compare_sources_sem_fonte(self) -> None:
        df = pd.DataFrame({"nome": ["A"], "preco": [10.0], "url": ["http://a.com"]})
        result = compare_sources(df)
        assert result.empty


class TestSummaryReport:
    def test_summary_report_conteudo(self, sample_df: pd.DataFrame) -> None:
        report = summary_report(sample_df)
        assert "RELATORIO DE PRECOS" in report
        assert "Total de produtos: 5" in report

    def test_summary_report_com_fonte(self, sample_df: pd.DataFrame) -> None:
        report = summary_report(sample_df)
        assert "POR FONTE" in report
        assert "site1" in report
        assert "site2" in report

    def test_summary_report_salva_arquivo(self, sample_df: pd.DataFrame, tmp_path: Path) -> None:
        output_path = str(tmp_path / "relatorio.txt")
        summary_report(sample_df, output_path=output_path)
        assert Path(output_path).exists()

    def test_summary_report_retorna_string(self, sample_df: pd.DataFrame) -> None:
        report = summary_report(sample_df)
        assert isinstance(report, str)
