"""Testes para o modulo de banco de dados."""

import csv
from pathlib import Path

import pytest

from src.db import DatabaseManager, ProdutoRecord


@pytest.fixture
def db(tmp_path) -> DatabaseManager:
    db_path = str(tmp_path / "test.db")
    return DatabaseManager(db_path=db_path)


@pytest.fixture
def sample_products() -> list[dict]:
    return [
        {"nome": "Notebook Dell", "preco": 3500.0, "url": "http://example.com/1"},
        {"nome": "Mouse Logitech", "preco": 129.9, "url": "http://example.com/2"},
        {"nome": "Teclado Mecanico", "preco": 299.0, "url": "http://example.com/3"},
    ]


class TestDatabaseManager:
    def test_init(self, db: DatabaseManager) -> None:
        assert db.engine is not None
        assert db.count_products() == 0

    def test_insert_products(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        count = db.insert_products(sample_products)
        assert count == 3
        assert db.count_products() == 3

    def test_insert_products_with_fonte(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products, fonte="test_site")
        products = db.query_all()
        assert all(p["fonte"] == "test_site" for p in products)

    def test_insert_skip_duplicates(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        count = db.insert_products(sample_products, skip_duplicates=True)
        assert count == 0
        assert db.count_products() == 3

    def test_insert_no_skip_duplicates(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products, skip_duplicates=False)
        db.insert_products(sample_products, skip_duplicates=False)
        assert db.count_products() == 6

    def test_query_all(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        results = db.query_all()
        assert len(results) == 3
        assert results[0]["nome"] == "Notebook Dell"
        assert results[0]["preco"] == 3500.0
        assert "data_coleta" in results[0]

    def test_query_all_vazio(self, db: DatabaseManager) -> None:
        results = db.query_all()
        assert len(results) == 0

    def test_query_filtered_by_fonte(self, db: DatabaseManager) -> None:
        db.insert_products([
            {"nome": "A", "preco": 10.0, "url": "http://a.com"},
            {"nome": "B", "preco": 20.0, "url": "http://b.com"},
        ], fonte="site1")
        db.insert_products([
            {"nome": "C", "preco": 30.0, "url": "http://c.com"},
        ], fonte="site2")

        results = db.query_filtered(fonte="site1")
        assert len(results) == 2

    def test_query_filtered_by_price(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        results = db.query_filtered(min_price=100.0, max_price=500.0)
        assert len(results) == 2

    def test_query_filtered_by_search(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        results = db.query_filtered(search="Dell")
        assert len(results) == 1
        assert results[0]["nome"] == "Notebook Dell"

    def test_query_filtered_order(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        results = db.query_filtered(order_by="preco")
        assert results[0]["preco"] == 129.9
        assert results[-1]["preco"] == 3500.0

    def test_query_filtered_limit(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        results = db.query_filtered(limit=2)
        assert len(results) == 2

    def test_query_by_price_range(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        results = db.query_by_price_range(100.0, 500.0)
        assert len(results) == 2

    def test_count_products(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        assert db.count_products() == 0
        db.insert_products(sample_products)
        assert db.count_products() == 3

    def test_count_products_by_fonte(self, db: DatabaseManager) -> None:
        db.insert_products([{"nome": "A", "preco": 10.0, "url": "http://a.com"}], fonte="s1")
        db.insert_products([{"nome": "B", "preco": 20.0, "url": "http://b.com"}], fonte="s2")
        assert db.count_products(fonte="s1") == 1

    def test_get_sources(self, db: DatabaseManager) -> None:
        db.insert_products([{"nome": "A", "preco": 10.0, "url": "http://a.com"}], fonte="site1")
        db.insert_products([{"nome": "B", "preco": 20.0, "url": "http://b.com"}], fonte="site2")
        sources = db.get_sources()
        assert set(sources) == {"site1", "site2"}

    def test_insert_from_csv(self, db: DatabaseManager, tmp_path: Path) -> None:
        csv_path = str(tmp_path / "test.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["nome", "preco", "url", "fonte"])
            writer.writerow(["Livro A", "10.99", "http://a.com", "site1"])
            writer.writerow(["Livro B", "20.50", "http://b.com", "site1"])

        count = db.insert_from_csv(csv_path)
        assert count == 2
        assert db.count_products() == 2

    def test_delete_all(self, db: DatabaseManager, sample_products: list[dict]) -> None:
        db.insert_products(sample_products)
        assert db.count_products() == 3
        deleted = db.delete_all()
        assert deleted == 3
        assert db.count_products() == 0

    def test_produto_record_repr(self) -> None:
        record = ProdutoRecord(nome="Teste", preco=10.0, url="http://test.com")
        assert "Teste" in repr(record)
        assert "10.0" in repr(record)
