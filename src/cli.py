"""Interface de linha de comando para o projeto de web scraping."""

import argparse
import logging
import sys

from src.log_config import setup_logging


def cmd_scrape(args: argparse.Namespace) -> None:
    """Executa o scraping de produtos."""
    from src.scraper import ProductScraper

    scraper = ProductScraper(delay=args.delay)
    produtos = scraper.fetch_and_save(
        url=args.url,
        name_selector=args.name_selector,
        price_selector=args.price_selector,
        filepath=args.output,
        fonte=args.fonte,
        append=args.append,
        save_db=args.save_db,
        db_path=args.db_path,
        max_pages=args.max_pages,
    )
    if produtos:
        logging.info("Scraping concluido: %d produtos coletados", len(produtos))
    else:
        logging.warning("Nenhum produto foi coletado")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Executa a analise dos dados."""
    from src.analyze import (
        calc_stats,
        compare_prices,
        compare_sources,
        load_data,
        plot_price_distribution,
    )

    df = load_data(args.input)

    stats = calc_stats(df)
    logging.info("=== Estatisticas ===")
    for key, value in stats.items():
        logging.info("  %s: %.2f", key, value)

    plot_price_distribution(df, output_path=f"{args.output_dir}/distribuicao.png")

    comparacao = compare_prices(df, top_n=args.top_n)
    comparacao.to_csv(f"{args.output_dir}/comparacao.csv", index=False)

    cross = compare_sources(df)
    if not cross.empty:
        cross.to_csv(f"{args.output_dir}/cross_site.csv", index=False)
        logging.info("Comparacao cross-site salva em %s/cross_site.csv", args.output_dir)

    logging.info("Resultados salvos em %s", args.output_dir)


def cmd_report(args: argparse.Namespace) -> None:
    """Gera um relatorio resumido."""
    from src.analyze import load_data, summary_report

    df = load_data(args.input)
    report = summary_report(df, output_path=args.output)
    print(report)


def cmd_db_import(args: argparse.Namespace) -> None:
    """Importa CSV para o banco de dados."""
    from src.db import DatabaseManager

    db = DatabaseManager(db_path=args.db_path)
    count = db.insert_from_csv(args.csv_path, fonte=args.fonte)
    logging.info("Importados %d produtos para o banco", count)


def cmd_db_list(args: argparse.Namespace) -> None:
    """Lista produtos do banco com filtros."""
    from src.db import DatabaseManager

    db = DatabaseManager(db_path=args.db_path)
    products = db.query_filtered(
        fonte=args.fonte,
        min_price=args.min_price,
        max_price=args.max_price,
        search=args.search,
        order_by=args.order or "id",
        limit=args.limit,
    )

    if not products:
        logging.info("Nenhum produto encontrado no banco")
        return

    logging.info("=== Produtos no Banco (%d total) ===", len(products))
    for p in products:
        logging.info(
            "  [%d] %s - %.2f (%s) [%s]",
            p["id"],
            p["nome"],
            p["preco"],
            p["fonte"] or "N/A",
            p["data_coleta"] or "N/A",
        )


def cmd_db_clear(args: argparse.Namespace) -> None:
    """Remove todos os registros do banco."""
    from src.db import DatabaseManager

    db = DatabaseManager(db_path=args.db_path)
    deleted = db.delete_all()
    logging.info("Removidos %d registros do banco", deleted)


def cmd_db_sources(args: argparse.Namespace) -> None:
    """Lista fontes distintas no banco."""
    from src.db import DatabaseManager

    db = DatabaseManager(db_path=args.db_path)
    sources = db.get_sources()

    if not sources:
        logging.info("Nenhuma fonte encontrada no banco")
        return

    logging.info("=== Fontes no Banco ===")
    for s in sources:
        count = db.count_products(fonte=s)
        logging.info("  %s: %d produtos", s, count)


def main() -> None:
    """Ponto de entrada principal do CLI."""
    parser = argparse.ArgumentParser(
        prog="web-scraping-precos",
        description="Ferramenta de web scraping e analise de precos",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Ativar logging detalhado (DEBUG)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponiveis")

    # scrape
    sp = subparsers.add_parser("scrape", help="Executar scraping de produtos")
    sp.add_argument("--url", required=True, help="URL da pagina")
    sp.add_argument("--name-selector", required=True, help="Seletor CSS para nome")
    sp.add_argument("--price-selector", required=True, help="Seletor CSS para preco")
    sp.add_argument("--output", default="data/produtos.csv", help="CSV de saida")
    sp.add_argument("--fonte", default="", help="Nome da fonte/site")
    sp.add_argument("--delay", type=float, default=1.0, help="Delay entre requisicoes")
    sp.add_argument("--max-pages", type=int, default=1, help="Max paginas (0=todas)")
    sp.add_argument("--append", action="store_true", help="Anexar ao CSV existente")
    sp.add_argument("--save-db", action="store_true", help="Salvar tambem no SQLite")
    sp.add_argument("--db-path", default="data/produtos.db", help="Caminho do SQLite")
    sp.set_defaults(func=cmd_scrape)

    # analyze
    sp = subparsers.add_parser("analyze", help="Analisar dados coletados")
    sp.add_argument("--input", default="data/produtos.csv", help="CSV/JSON de entrada")
    sp.add_argument("--output-dir", default="outputs", help="Diretorio de saida")
    sp.add_argument("--top-n", type=int, default=10, help="Top N para comparacao")
    sp.set_defaults(func=cmd_analyze)

    # report
    sp = subparsers.add_parser("report", help="Gerar relatorio resumido")
    sp.add_argument("--input", default="data/produtos.csv", help="CSV de entrada")
    sp.add_argument("--output", default="data/relatorio.txt", help="Relatorio de saida")
    sp.set_defaults(func=cmd_report)

    # db-import
    sp = subparsers.add_parser("db-import", help="Importar CSV para o banco")
    sp.add_argument("csv_path", help="Caminho do CSV para importar")
    sp.add_argument("--fonte", default=None, help="Nome da fonte")
    sp.add_argument("--db-path", default="data/produtos.db", help="Caminho do SQLite")
    sp.set_defaults(func=cmd_db_import)

    # db-list
    sp = subparsers.add_parser("db-list", help="Listar produtos do banco")
    sp.add_argument("--db-path", default="data/produtos.db", help="Caminho do SQLite")
    sp.add_argument("--fonte", default=None, help="Filtrar por fonte")
    sp.add_argument("--min-price", type=float, default=None, help="Preco minimo")
    sp.add_argument("--max-price", type=float, default=None, help="Preco maximo")
    sp.add_argument("--search", default=None, help="Buscar no nome")
    sp.add_argument("--order", default="id", choices=["id", "preco", "nome", "fonte"], help="Ordenar por")
    sp.add_argument("--limit", type=int, default=0, help="Limite de resultados (0=todos)")
    sp.set_defaults(func=cmd_db_list)

    # db-clear
    sp = subparsers.add_parser("db-clear", help="Limpar todos os registros")
    sp.add_argument("--db-path", default="data/produtos.db", help="Caminho do SQLite")
    sp.set_defaults(func=cmd_db_clear)

    # db-sources
    sp = subparsers.add_parser("db-sources", help="Listar fontes no banco")
    sp.add_argument("--db-path", default="data/produtos.db", help="Caminho do SQLite")
    sp.set_defaults(func=cmd_db_sources)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
