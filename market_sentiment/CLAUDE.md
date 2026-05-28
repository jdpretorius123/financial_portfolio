# Market Sentiment and Real-Time Financial Intelligence

This is a project for my financial analysis portfolio. I am trying to get a job as a financial analyst. This project uses the following tech stack (see "Tech Stack").

# Tech Stack
- Data Lake: Cloudflare R2
- Data Warehouse: BigQuery
- APIs:
    - Alpha Vantage
        - [https://www.alphavantage.co/documentation/#news-sentiment](Alpha Vantage Documentation)
    - NewsAPI
        - [https://newsapi.org/docs](NewsAPI Documentation)
- Scripting Language: Python
- Dashboard:
    - D3.js
    - HTML/JS

# GitHub Repository
- [https://github.com/jdpretorius123/financial_portfolio](link)

# Code Style
- Current PEP8 standards
    - I am applying PEP8 standards through the Ruff extension in VS Code

# Python Version
- Pinned to **3.12.0** via `.python-version` (managed by pyenv-win at `C:\Users\justi\.pyenv\pyenv-win\versions\3.12.0`)
- Virtual environment at `market_sentiment/.venv/` (thin venv, ensurepip-based, Windows layout)
- Activate (PowerShell): `.venv\Scripts\Activate.ps1`
- Reason for 3.12 over 3.14: broader pre-built wheel support for `google-cloud-bigquery` and `boto3`

# Working Agreement — Hint Mode
- **Justin writes the code.** Claude provides hints, decision tradeoffs, and documentation pointers.
- **Claude does NOT write Justin's code unless explicitly asked.** This includes config files, source modules, and tests. Markdown docs (like this file) and Claude's own memory are exceptions when Justin asks.
- Justin is a beginner across the stack and wants to understand the *why*, not just the *how*. Explanations should include rationale, not just instructions.
- When in doubt about scope, ask before coding.

# Common Commands
*(Run from `C:\Users\justi\Desktop\financial_portfolio\market_sentiment\`. Activate the venv first.)*

| Command | Purpose |
|---|---|
| `.venv\Scripts\Activate.ps1` | Activate the venv (PowerShell) |
| `python --version` | Confirm 3.12.0 |
| `pip install -e ".[dev]"` | Install project (editable mode) + runtime + dev deps from `pyproject.toml` |
| `pip freeze > requirements.txt` | Refresh the lockfile snapshot after adding/upgrading deps |
| `ruff check .` | Lint |
| `ruff check . --fix` | Auto-fix lint where safe |
| `ruff format .` | Format |
| `pytest` | Run tests (collected from `tests/` per pytest config in `pyproject.toml`) |

# Data Flow

```
Alpha Vantage NEWS_SENTIMENT  ─┐
                                ├→  Cloudflare R2  (raw JSON, data lake)
NewsAPI /everything            ─┘
                                │
                                ↓  Python ETL
                                │     pydantic v2  — validate API responses
                                │     nltk         — tokenize, stopwords
                                │     VADER        — sentiment scoring (compound -1..+1)
                                │
                                ↓
                            BigQuery  (structured + scored, data warehouse)
                                │
                                ↓  SQL queries
                                │
                                ↓
                          D3.js dashboard  (HTML/JS)
                          ├─ streamgraph (sentiment over time)
                          ├─ force-directed entity-relationship graph
                          └─ sentiment-emotion radar chart
```

# Project Decisions
*(Decided as of 2026-05-06. If any of these reverse, update this section so future sessions don't act on stale assumptions.)*

- **Cadence**: monthly batch
- **Ticker slice**: ~10 mixed-cap tech sector tickers
- **Backfill window**: 4 weeks on first run (one month per API call; cadence is monthly)
- **API access**: REST only (no MCP)
- **NewsAPI auth**: `apiKey` query parameter (decision reversed 2026-05-15 — NewsAPI supports both forms; Justin elected to keep the simpler query-param form to match the Alpha Vantage client's pattern)
- **Data lake format**: JSON in R2; `pyarrow`/parquet deferred until volume justifies it
- **Sentiment library**: `nltk.sentiment.vader.SentimentIntensityAnalyzer` (NOT the standalone `vaderSentiment` PyPI package — same algorithm, redundant)
- **Dependency manifest**: **`pyproject.toml`** with `hatchling` as the build backend. The project is structured as an installable package (`src/` layout) so `pip install -e ".[dev]"` pulls runtime + dev deps in one shot. `pyproject.toml` holds direct deps with `>=` ranges, plus all `[tool.*]` config (Ruff, pytest).
- **Lockfile**: `requirements.txt` is kept alongside `pyproject.toml` as a frozen snapshot of every installed package (transitive deps included, exact `==` pins). Regenerated with `pip freeze > requirements.txt` after dep changes. Not edited by hand.
- **Credentials — R2**: keys via env vars loaded by `python-dotenv` from `.env` (git-ignored). `.env.example` is checked in as a template.
- **Credentials — GCP**: Application Default Credentials (ADC) via `gcloud auth application-default login` — no env var, no JSON key file (decision reversed 2026-05-16 — original plan was a service-account JSON key via `GOOGLE_APPLICATION_CREDENTIALS`, but new GCP orgs block JSON key creation by default under the `iam.disableServiceAccountKeyCreation` org policy, and ADC user credentials are Google's recommended pattern for local development anyway; JSON keys are the most-leaked cloud-credential type and now actively discouraged). `bigquery.Client()` picks up ADC automatically. One-time setup: `gcloud auth application-default login`, then `gcloud config set project <id>` and `gcloud auth application-default set-quota-project <id>` so the active project and ADC quota project align.
- **Code style — formatter** (Ruff `[tool.ruff.format]`):
  - `quote-style = "double"` (Black/PSF convention)
  - `indent-style = "space"` (PEP8 — explicit declaration)
  - `line-ending = "lf"` (forces Unix line endings everywhere; avoids CRLF/LF git churn on Windows)
  - `docstring-code-format = true` with `docstring-code-line-length = 72` (Python code blocks inside docstrings get formatted; narrower limit because docstring code is rendered with extra indentation)
  - `line-length = 88` (Black/Ruff default; relaxed from PEP8's 79)
- **Code style — linter** (Ruff `[tool.ruff.lint]`):
  - Rule sets enabled: `E` (pycodestyle errors / PEP8), `F` (pyflakes), `I` (isort), `B` (bugbear), `UP` (pyupgrade), `D` (pydocstyle)
  - Per-file ignores: `__init__.py` ignores `D104`; `tests/**/*.py` ignores `D100`–`D103` (test functions don't need docstrings)
- **Docstring convention**: **Google style** (configured via `[tool.ruff.lint.pydocstyle] convention = "google"`). Reasoning: cleaner section headers (`Args:`, `Returns:`, `Raises:`), easier to read at a glance, common in modern Python data work. Example:
  ```python
  def fetch_articles(ticker: str, since: datetime) -> list[Article]:
      """Fetch news articles for a ticker since a given date.

      Args:
          ticker: Stock ticker symbol, e.g. "AAPL".
          since: Earliest publication date to include (UTC).

      Returns:
          Articles with `title`, `url`, `published_at`, and `body` fields.

      Raises:
          AlphaVantageRateLimitError: If the API throttles the request.
      """
  ```

# Project Layout
```
market_sentiment/
├── pyproject.toml          # build config, deps, tool config (Ruff, pytest)
├── requirements.txt        # frozen lockfile (pip freeze output)
├── README.md               # project overview
├── CLAUDE.md               # this file
├── .python-version         # pyenv pin → 3.12.0
├── .env                    # secrets, NOT committed
├── .env.example            # template for required env vars, committed
├── .venv/                  # local virtual environment (git-ignored)
├── .claude/
│   └── agents/
│       ├── codebase-analyzer.md
│       └── script-error-auditor.md
├── src/
│   └── market_sentiment/             # the importable Python package
│       ├── __init__.py               # marks this dir as a package
│       ├── acquisition/              # Alpha Vantage + NewsAPI clients
│       │   └── __init__.py
│       ├── etl/                      # validation, cleaning, sentiment scoring
│       │   └── __init__.py
│       └── warehouse/                # R2 ↔ BigQuery loaders
│           └── __init__.py
├── dashboard/              # HTML/D3/JS
└── tests/                  # pytest
```

# Where to Find Things Across Sessions
- **Plans**: `C:\Users\justi\.claude\plans\`
  - Current: `floating-wibbling-pike.md` (scaffolding verification + auditor restriction)
  - Original scaffolding plan: `launch-an-agent-to-steady-milner.md`
- **Claude's memory**: `C:\Users\justi\.claude\projects\C--Users-justi-Desktop-financial-portfolio-market-sentiment\memory\`
- **Umbrella repo**: `C:\Users\justi\Desktop\financial_portfolio\` (5 sibling projects: market_sentiment, crm_and_clv_scoring, forecasting_and_optimization, logistics_performance, pricing_and_monitoring)

# Custom Agents Available in This Project
- **`script-error-auditor`** at `.claude/agents/script-error-auditor.md` — reviews Python scripts for syntax / runtime / logical errors. Read-only with respect to user files; only writes to its own agent-memory directory at `.claude/agent-memory/script-error-auditor/`. If it finds a fix, it reports the fix and waits for Justin to apply it.
- **`codebase-analyzer`** at `.claude/agents/codebase-analyzer.md` — analyzes existing codebase structure and patterns before planning, refactoring, or feature work.
