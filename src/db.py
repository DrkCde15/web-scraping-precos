"""Modulo de gerenciamento do banco de dados SQLite."""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


def _parse_datetime(value) -> Optional[datetime]:
    """Converte valor para datetime, aceitando string ISO ou datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


class ProdutoRecord(Base):
    """Tabela de produtos no banco de dados."""

    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(500), nullable=False)
    preco = Column(Float, nullable=False)
    url = Column(String(2000), nullable=True)
    fonte = Column(String(200), nullable=True)
    data_coleta = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Produto(id={self.id}, nome='{self.nome}', preco={self.preco})>"


class DatabaseManager:
    """Gerencia operacoes no banco de dados SQLite."""

    def __init__(self, db_path: str = "data/produtos.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Banco de dados inicializado em %s", db_path)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def _url_exists(self, session: Session, url: str) -> bool:
        """Verifica se uma URL ja existe no banco."""
        if not url:
            return False
        return session.query(ProdutoRecord).filter(ProdutoRecord.url == url).first() is not None

    def insert_products(
        self,
        products: list[dict[str, str | float]],
        fonte: Optional[str] = None,
        skip_duplicates: bool = True,
    ) -> int:
        """
        Insere multiplos produtos no banco.

        Args:
            products: Lista de dicts com chaves 'nome', 'preco', 'url'
            fonte: Nome da fonte/site
            skip_duplicates: Se True, ignora produtos com URL duplicada

        Returns:
            Quantidade de produtos inseridos
        """
        count = 0
        duplicatas = 0
        with self.get_session() as session:
            for p in products:
                url = p.get("url", "")
                if skip_duplicates and self._url_exists(session, url):
                    duplicatas += 1
                    continue

                record = ProdutoRecord(
                    nome=p["nome"],
                    preco=float(p["preco"]),
                    url=url,
                    fonte=fonte or p.get("fonte"),
                    data_coleta=_parse_datetime(p.get("data_coleta")),
                )
                session.add(record)
                count += 1
            session.commit()

        if duplicatas > 0:
            logger.info("Ignoradas %d duplicatas", duplicatas)
        logger.info("Inseridos %d produtos no banco", count)
        return count

    def insert_from_csv(self, csv_path: str, fonte: Optional[str] = None, skip_duplicates: bool = True) -> int:
        """Importa produtos de um arquivo CSV para o banco."""
        count = 0
        duplicatas = 0
        with self.get_session() as session:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("url", "")
                    if skip_duplicates and self._url_exists(session, url):
                        duplicatas += 1
                        continue

                    preco_str = str(row.get("preco", "0"))
                    record = ProdutoRecord(
                        nome=row.get("nome", ""),
                        preco=float(preco_str),
                        url=url,
                        fonte=fonte or row.get("fonte"),
                        data_coleta=_parse_datetime(row.get("data_coleta")),
                    )
                    session.add(record)
                    count += 1
            session.commit()

        if duplicatas > 0:
            logger.info("Ignoradas %d duplicatas", duplicatas)
        logger.info("Importados %d produtos de %s", count, csv_path)
        return count

    def query_all(self) -> list[dict]:
        with self.get_session() as session:
            results = session.query(ProdutoRecord).all()
            return [
                {
                    "id": r.id,
                    "nome": r.nome,
                    "preco": r.preco,
                    "url": r.url,
                    "fonte": r.fonte,
                    "data_coleta": r.data_coleta.isoformat() if r.data_coleta else None,
                }
                for r in results
            ]

    def query_filtered(
        self,
        fonte: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        order_by: str = "id",
        limit: int = 0,
    ) -> list[dict]:
        """
        Consulta produtor com filtros avancados.
        """
        with self.get_session() as session:
            query = session.query(ProdutoRecord)

            if fonte:
                query = query.filter(ProdutoRecord.fonte == fonte)
            if min_price is not None:
                query = query.filter(ProdutoRecord.preco >= min_price)
            if max_price is not None:
                query = query.filter(ProdutoRecord.preco <= max_price)
            if search:
                query = query.filter(ProdutoRecord.nome.contains(search))

            order_col = getattr(ProdutoRecord, order_by, ProdutoRecord.id)
            query = query.order_by(order_col)

            if limit > 0:
                query = query.limit(limit)

            results = query.all()
            return [
                {
                    "id": r.id,
                    "nome": r.nome,
                    "preco": r.preco,
                    "url": r.url,
                    "fonte": r.fonte,
                    "data_coleta": r.data_coleta.isoformat() if r.data_coleta else None,
                }
                for r in results
            ]

    def query_by_price_range(self, min_price: float, max_price: float) -> list[dict]:
        return self.query_filtered(min_price=min_price, max_price=max_price)

    def count_products(self, fonte: Optional[str] = None) -> int:
        with self.get_session() as session:
            query = session.query(ProdutoRecord)
            if fonte:
                query = query.filter(ProdutoRecord.fonte == fonte)
            return query.count()

    def get_sources(self) -> list[str]:
        """Retorna lista de fontes distintas no banco."""
        with self.get_session() as session:
            results = session.query(ProdutoRecord.fonte).distinct().all()
            return [r[0] for r in results if r[0]]

    def delete_all(self) -> int:
        with self.get_session() as session:
            count = session.query(ProdutoRecord).delete()
            session.commit()
        logger.info("Removidos %d registros do banco", count)
        return count
