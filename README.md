# Web Scraping de Precos

Projeto de Web Scraping e Analise de Precos usando Python. Coleta dados de sites de e-commerce, armazena em CSV/JSON/SQLite e gera analises estatisticas.

## Funcionalidades

- **Scraping**: paginacao automatica, retry com backoff exponencial, progress bar
- **Armazenamento**: CSV (modo append), JSON e SQLite com deteccao de duplicatas
- **Analise**: estatisticas descritivas, distribuicao de precos, comparacao cross-site
- **CLI**: interface completa via linha de comando
- **Testes**: 48 testes unitarios com pytest

## Instalacao

```bash
# Clonar o repositorio
git clone <url-do-repositorio>
cd 01-web-scraping-precos

# Criar e ativar virtualenv
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Scraping

```bash
python -m src scrape \
  --url "https://books.toscrape.com/" \
  --name-selector "h3 a" \
  --price-selector "p.price_color" \
  --fonte "books.toscrape.com" \
  --max-pages 5 \
  --output "data/books.csv" \
  --save-db
```

**Parametros:**

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| `--url` | Sim | URL da pagina inicial |
| `--name-selector` | Sim | Seletor CSS para o nome do produto |
| `--price-selector` | Sim | Seletor CSS para o preco |
| `--fonte` | Nao | Nome da fonte/site para identificacao |
| `--max-pages` | Nao | Numero de paginas (0 = todas, padrao: 1) |
| `--output` | Nao | Caminho do CSV de saida (padrao: `data/produtos.csv`) |
| `--delay` | Nao | Delay entre paginas em segundos (padrao: 1.0) |
| `--append` | Nao | Anexar ao CSV existente ao inves de sobrescrever |
| `--save-db` | Nao | Salvar tambem no banco SQLite |
| `--db-path` | Nao | Caminho do banco SQLite (padrao: `data/produtos.db`) |

**Exemplo com todos os parametros:**

```bash
python -m src scrape \
  --url "https://books.toscrape.com/" \
  --name-selector "h3 a" \
  --price-selector "p.price_color" \
  --fonte "books.toscrape.com" \
  --max-pages 3 \
  --output "data/books.csv" \
  --delay 2.0 \
  --append \
  --save-db
```

### Como encontrar os seletores CSS

1. Abra o site no navegador
2. Clique com o botao direito no nome do produto > "Inspecionar"
3. Identifique o seletor CSS do elemento

**Exemplos comuns:**

| Site | Seletor Nome | Seletor Preco |
|------|-------------|---------------|
| books.toscrape.com | `h3 a` | `p.price_color` |
| Amazon (exemplo) | `span.a-text-normal` | `span.a-price-whole` |
| Mercado Livre (exemplo) | `h2.poly-component__title` | `span.andes-money-amount__fraction` |

### Analise

```bash
# Analise completa (estatisticas + graficos + comparacao)
python -m src analyze --input "data/books.csv" --output-dir "outputs/books"

# Relatorio textual
python -m src report --input "data/books.csv"
```

**Saida da analise:**

```
=== Estatisticas ===
  media: 35.00
  mediana: 33.48
  desvio_padrao: 14.55
  minimo: 12.84
  maximo: 57.31
  qtd_produtos: 60.00
```

**Arquivos gerados:**

| Arquivo | Descricao |
|---------|-----------|
| `outputs/distribuicao.png` | Histograma + boxplot de precos |
| `outputs/comparacao.csv` | Top N mais baratos e mais caros |
| `outputs/cross_site.csv` | Estatisticas por fonte/site |

### Banco de Dados

```bash
# Importar CSV existente para o banco
python -m src db-import data/books.csv --fonte "books.toscrape.com"

# Listar todos os produtos
python -m src db-list

# Listar com filtros
python -m src db-list --fonte "books.toscrape.com" --min-price 10 --max-price 50
python -m src db-list --search "Dell" --order preco --limit 10

# Listar fontes cadastradas
python -m src db-sources

# Limpar todos os registros
python -m src db-clear
```

**Filtros disponiveis para `db-list`:**

| Filtro | Descricao |
|--------|-----------|
| `--fonte` | Filtrar por fonte/site |
| `--min-price` | Preco minimo |
| `--max-price` | Preco maximo |
| `--search` | Buscar no nome do produto |
| `--order` | Ordenar por: `id`, `preco`, `nome`, `fonte` |
| `--limit` | Limite de resultados (0 = todos) |

### Uso via Python

```python
# Scraping
from src.scraper import ProductScraper

scraper = ProductScraper(delay=1.0)
produtos = scraper.fetch_and_save(
    url="https://books.toscrape.com/",
    name_selector="h3 a",
    price_selector="p.price_color",
    fonte="books.toscrape.com",
    max_pages=5,
    save_db=True,
)

# Analise
from src.analyze import load_data, calc_stats, compare_sources

df = load_data("data/books.csv")
stats = calc_stats(df)
cross = compare_sources(df)

# Banco de dados
from src.db import DatabaseManager

db = DatabaseManager()
db.insert_from_csv("data/books.csv", fonte="books.toscrape.com")
results = db.query_filtered(fonte="books.toscrape.com", min_price=10, max_price=50)
```

## Estrutura do Projeto

```
01-web-scraping-precos/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── __main__.py          # Entry point: python -m src
│   ├── cli.py               # Interface de linha de comando
│   ├── scraper.py           # Web scraping com paginacao
│   ├── analyze.py           # Analise de dados
│   ├── db.py                # Banco de dados SQLite
│   └── log_config.py        # Configuracao de logging
├── data/                    # Dados coletados (CSV, JSON, SQLite)
├── outputs/                 # Graficos e relatorios
├── notebooks/
│   └── 01_exploracao.ipynb  # Notebook de exploracao
└── tests/
    ├── __init__.py
    ├── test_scraper.py      # 16 testes
    ├── test_db.py           # 16 testes
    └── test_analyze.py      # 16 testes
```

## Comandos do CLI

| Comando | Descricao |
|---------|-----------|
| `scrape` | Coletar produtos de um site |
| `analyze` | Gerar estatisticas e graficos |
| `report` | Gerar relatorio textual |
| `db-import` | Importar CSV para o banco |
| `db-list` | Listar produtos do banco |
| `db-sources` | Listar fontes cadastradas |
| `db-clear` | Limpar todos os registros |

**Ajuda:**

```bash
python -m src --help
python -m src scrape --help
python -m src -v <comando>  # modo verbose (DEBUG)
```

## Testes

```bash
# Rodar todos os testes
python -m pytest tests/ -v

# Rodar testes de um modulo especifico
python -m pytest tests/test_scraper.py -v
python -m pytest tests/test_db.py -v
python -m pytest tests/test_analyze.py -v
```

## Observacoes

- Respeite os termos de uso dos sites alvo
- Use intervalos entre requisicoes (`--delay`) para nao sobrecarregar servidores
- O scraping e para fins educacionais
- Para sites que renderizam conteudo com JavaScript, e necessario usar Selenium ou Playwright
