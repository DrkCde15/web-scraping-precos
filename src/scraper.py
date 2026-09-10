"""Modulo de web scraping para extrair precos de produtos."""

import csv
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

logger = logging.getLogger(__name__)


@dataclass
class Produto:
    """Representa um produto coletado."""

    nome: str
    preco: float
    url: str
    fonte: str = ""
    data_coleta: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class ProductScraper:
    """Classe principal para scraping de produtos."""

    def __init__(self, delay: float = 1.0) -> None:
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        self._seen_urls: set[str] = set()

    def fetch_page(
        self,
        url: str,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> Optional[BeautifulSoup]:
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")
            except requests.RequestException as e:
                logger.warning(
                    "Tentativa %d/%d falhou para %s: %s",
                    attempt, max_retries, url, e,
                )
                if attempt < max_retries:
                    wait = backoff_factor**attempt
                    logger.info("Aguardando %.1f segundos", wait)
                    time.sleep(wait)

        logger.error("Todas as %d tentativas falharam para %s", max_retries, url)
        return None

    def find_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Encontra o link da proxima pagina."""
        from urllib.parse import urljoin

        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            return urljoin(current_url, next_link["href"])
        return None

    def parse_products(
        self,
        soup: BeautifulSoup,
        name_selector: str,
        price_selector: str,
        base_url: str = "",
    ) -> list[Produto]:
        produtos: list[Produto] = []

        nome_elements = soup.select(name_selector)
        preco_elements = soup.select(price_selector)

        for nome_el, preco_el in zip(nome_elements, preco_elements):
            nome = nome_el.get_text(strip=True)
            preco_texto = preco_el.get_text(strip=True)

            preco_texto = re.sub(r"[^\d.,]", "", preco_texto)
            if "," in preco_texto and "." in preco_texto:
                preco_texto = preco_texto.replace(".", "").replace(",", ".")
            elif "," in preco_texto:
                preco_texto = preco_texto.replace(",", ".")
            preco_texto = preco_texto.strip()
            try:
                preco = float(preco_texto)
            except ValueError:
                logger.warning("Nao foi possivel converter preco: '%s'", preco_texto)
                continue

            url = ""
            href = None
            if nome_el.name == "a" and nome_el.get("href"):
                href = nome_el["href"]
            else:
                link = nome_el.find("a")
                if link and link.get("href"):
                    href = link["href"]
            if href:
                if href.startswith("http"):
                    url = href
                elif href.startswith("/"):
                    url = f"{base_url}{href}"
                else:
                    url = f"{base_url}/{href}"

            produtos.append(Produto(nome=nome, preco=preco, url=url))

        logger.info("Extraidos %d produtos da pagina", len(produtos))
        return produtos

    def _is_duplicate(self, url: str) -> bool:
        """Verifica se a URL ja foi coletada nesta sessao."""
        if url in self._seen_urls:
            return True
        self._seen_urls.add(url)
        return False

    def save_to_csv(
        self,
        produtos: list[Produto],
        filepath: str = "data/produtos.csv",
        append: bool = False,
    ) -> int:
        """
        Salva produtos em CSV. Retorna quantidade de linhas escritas.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        write_mode = "a" if append else "w"
        write_header = not (append and path.exists())

        with open(path, write_mode, newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["nome", "preco", "url", "fonte", "data_coleta"])
            for p in produtos:
                writer.writerow([p.nome, p.preco, p.url, p.fonte, p.data_coleta])

        logger.info("Salvos %d produtos em %s (append=%s)", len(produtos), filepath, append)
        return len(produtos)

    def save_to_json(
        self,
        produtos: list[Produto],
        filepath: str = "data/produtos.json",
    ) -> None:
        """Salva produtos em JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        existing.extend([p.to_dict() for p in produtos])

        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        logger.info("Salvos %d produtos em %s (total: %d)", len(produtos), filepath, len(existing))

    def save_to_db(
        self,
        produtos: list[Produto],
        db_path: str = "data/produtos.db",
    ) -> int:
        """Insere produtos diretamente no banco SQLite."""
        from src.db import DatabaseManager

        db = DatabaseManager(db_path=db_path)
        products_dicts = [p.to_dict() for p in produtos]
        return db.insert_products(products_dicts, fonte=produtos[0].fonte if produtos else None)

    def fetch_and_save(
        self,
        url: str,
        name_selector: str,
        price_selector: str,
        filepath: str = "data/produtos.csv",
        fonte: str = "",
        append: bool = False,
        save_db: bool = False,
        db_path: str = "data/produtos.db",
        max_pages: int = 1,
    ) -> list[Produto]:
        """
        Busca paginas, extrai e salva produtos com suporte a paginacao.

        Args:
            url: URL da pagina inicial
            name_selector: Seletor CSS para nome
            price_selector: Seletor CSS para preco
            filepath: Caminho do CSV de saida
            fonte: Nome da fonte/site
            append: Se True, anexa ao CSV existente
            save_db: Se True, salva tambem no SQLite
            db_path: Caminho do banco SQLite
            max_pages: Numero maximo de paginas a coletar (0 = todas)

        Returns:
            Lista de produtos coletados
        """
        all_produtos: list[Produto] = []
        current_url: Optional[str] = url
        base_url = "/".join(url.split("/")[:3])
        page_count = 0

        pages = tqdm(desc="Coletando paginas", unit="pag") if max_pages != 1 else None

        while current_url:
            if max_pages > 0 and page_count >= max_pages:
                break

            soup = self.fetch_page(current_url)
            if not soup:
                break

            produtos = self.parse_products(soup, name_selector, price_selector, base_url)

            novos = []
            for p in produtos:
                p.fonte = fonte
                if not self._is_duplicate(p.url):
                    novos.append(p)

            all_produtos.extend(novos)
            page_count += 1

            if pages is not None:
                pages.update(1)
                pages.set_postfix(produtos=len(all_produtos))

            current_url = self.find_next_page(soup, current_url)
            if current_url:
                time.sleep(self.delay)

        if pages is not None:
            pages.close()

        if all_produtos:
            self.save_to_csv(all_produtos, filepath, append=append)
            if save_db:
                self.save_to_db(all_produtos, db_path=db_path)

        logger.info(
            "Scraping concluido: %d produtos novos em %d paginas",
            len(all_produtos), page_count,
        )
        return all_produtos
