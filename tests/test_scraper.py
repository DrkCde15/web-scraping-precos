"""Testes para o modulo de scraping."""

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.scraper import Produto, ProductScraper


@pytest.fixture
def scraper() -> ProductScraper:
    return ProductScraper(delay=0)


@pytest.fixture
def sample_html() -> str:
    return """
    <html>
    <body>
        <div class="product-card">
            <h2 class="product-name"><a href="/produto/1">Notebook Dell</a></h2>
            <span class="product-price">R$ 3.500,00</span>
        </div>
        <div class="product-card">
            <h2 class="product-name"><a href="/produto/2">Mouse Logitech</a></h2>
            <span class="product-price">R$ 129,90</span>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_next() -> str:
    return """
    <html>
    <body>
        <ol class="row">
            <li><article class="product_pod">
                <h3><a href="catalogue/book_1/index.html">Book 1</a></h3>
                <div class="product_price"><p class="price_color">£10.99</p></div>
            </article></li>
        </ol>
        <ul class="pager">
            <li class="next"><a href="catalogue/page-2.html">next</a></li>
        </ul>
    </body>
    </html>
    """


class TestProduto:
    def test_criar_produto(self) -> None:
        p = Produto(nome="Teste", preco=10.5, url="http://example.com")
        assert p.nome == "Teste"
        assert p.preco == 10.5
        assert p.url == "http://example.com"
        assert p.fonte == ""
        assert p.data_coleta is not None

    def test_produto_to_dict(self) -> None:
        p = Produto(nome="Teste", preco=10.5, url="http://example.com", fonte="site")
        d = p.to_dict()
        assert d["nome"] == "Teste"
        assert d["preco"] == 10.5
        assert d["fonte"] == "site"
        assert "data_coleta" in d


class TestProductScraper:
    def test_init(self, scraper: ProductScraper) -> None:
        assert scraper.delay == 0
        assert scraper.session is not None
        assert len(scraper._seen_urls) == 0

    @patch("src.scraper.requests.Session.get")
    def test_fetch_page_sucesso(self, mock_get: MagicMock, scraper: ProductScraper) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Ok</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = scraper.fetch_page("http://example.com")
        assert result is not None
        assert result.find("body").get_text() == "Ok"

    @patch("src.scraper.requests.Session.get")
    def test_fetch_page_erro(self, mock_get: MagicMock, scraper: ProductScraper) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError("Erro de conexao")
        result = scraper.fetch_page("http://example.com")
        assert result is None

    def test_parse_products(self, scraper: ProductScraper, sample_html: str) -> None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(sample_html, "html.parser")
        produtos = scraper.parse_products(
            soup,
            name_selector=".product-name",
            price_selector=".product-price",
            base_url="http://example.com",
        )

        assert len(produtos) == 2
        assert produtos[0].nome == "Notebook Dell"
        assert produtos[0].preco == 3500.0
        assert produtos[1].nome == "Mouse Logitech"
        assert produtos[1].preco == 129.9

    def test_parse_products_vazio(self, scraper: ProductScraper) -> None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        produtos = scraper.parse_products(
            soup,
            name_selector=".product-name",
            price_selector=".product-price",
        )
        assert len(produtos) == 0

    def test_save_to_csv(self, scraper: ProductScraper, tmp_path: Path) -> None:
        produtos = [
            Produto(nome="Produto A", preco=10.0, url="http://a.com"),
            Produto(nome="Produto B", preco=20.0, url="http://b.com"),
        ]

        filepath = str(tmp_path / "test_produtos.csv")
        count = scraper.save_to_csv(produtos, filepath)
        assert count == 2
        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0] == ["nome", "preco", "url", "fonte", "data_coleta"]
        assert rows[1][0] == "Produto A"
        assert rows[1][1] == "10.0"

    def test_save_to_csv_append(self, scraper: ProductScraper, tmp_path: Path) -> None:
        produtos1 = [Produto(nome="A", preco=10.0, url="http://a.com")]
        produtos2 = [Produto(nome="B", preco=20.0, url="http://b.com")]

        filepath = str(tmp_path / "test.csv")
        scraper.save_to_csv(produtos1, filepath, append=False)
        scraper.save_to_csv(produtos2, filepath, append=True)

        with open(filepath, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        assert len(rows) == 3
        assert rows[1][0] == "A"
        assert rows[2][0] == "B"

    def test_save_to_json(self, scraper: ProductScraper, tmp_path: Path) -> None:
        import json

        produtos = [Produto(nome="Teste", preco=10.0, url="http://test.com", fonte="site")]
        filepath = str(tmp_path / "test.json")

        scraper.save_to_json(produtos, filepath)
        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["nome"] == "Teste"
        assert data[0]["fonte"] == "site"

    def test_deteccao_duplicatas(self, scraper: ProductScraper) -> None:
        assert not scraper._is_duplicate("http://a.com")
        assert scraper._is_duplicate("http://a.com")
        assert not scraper._is_duplicate("http://b.com")

    def test_find_next_page(self, scraper: ProductScraper) -> None:
        from bs4 import BeautifulSoup

        html = '<html><body><ul class="pager"><li class="next"><a href="page-2.html">next</a></li></ul></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = scraper.find_next_page(soup, "http://example.com/catalogue/page-1.html")
        assert result == "http://example.com/catalogue/page-2.html"

    def test_find_next_page_none(self, scraper: ProductScraper) -> None:
        from bs4 import BeautifulSoup

        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = scraper.find_next_page(soup, "http://example.com")
        assert result is None
