## Metadata Validation Tool
Joshua Gray

### Summary

This is a metadata validation tool for the Dataverse academic repository system, and provides infrastructure for using the [metadig-py](https://github.com/UCSB-Library-Research-Data-Services/metadig-py/tree/master) metadata validation tool on the metadata for a given Dataset. Currently, the tool runs a suite of checks corresponding to FAIR data principles.

The application provides a web GUI for running and viewing the metadig reports, which is accessed in the form of an external tool in Dataverse. The core validation logic is also usable independently of the web GUI, as a standalone batch pipeline.

### Architecture

The project has two components that share the same validation code:

- **`backend/`** — a FastAPI app (`backend/src/main.py`) that Dataverse launches as an "external tool", registered via `backend/manifest.json` and shown under a dataset's **Explore** menu. Routes:
  - `GET /metadata-report` — the landing page Dataverse opens. It receives a base64-encoded `callback` query param from Dataverse, decodes it to fetch the dataset's metadata via Dataverse's signed-URL mechanism (`backend/src/utils/helpers.py`), and renders either `empty_dashboard.html` (no cached report yet) or `main_dashboard.html` (a cached report exists), backed by a sqlite cache (`backend/src/utils/db.py`, `backend/data/reports.db`). The frontend templates are rendered server-side using jinja2.
  - `POST /api/load-new-report` — re-fetches metadata for a dataset and re-runs the validator, caching the new report in the database.
  - `POST /api/toggle-check-visibility` — toggles whether a given check is shown on the dashboard at the discretion of the user.

  The signed-URL flow used here is distinct from the batch pipeline's token-based auth described below.

- **`tools/`** — the `validator` Python package: Fetches json metadata, translates it into Datacite XML, and runs the metadig-py engine. It can run standalone or be imported by the backend.
  - `retrieval/fetcher.py` — batch-mode retrieval: polls Dataverse's Search API (`X-Dataverse-key` token auth) for draft datasets updated since the last run.
  - `translation/translator.py` + `translation/handlers.py` + `translation/blocks/*.yaml` — a declarative translation engine from JSON into DataCite XML. Each YAML file in `translation/blocks/` maps one Dataverse metadata block to DataCite elements. Some mappings are too complex to express declaratively and instead rely on corresponding handler functions in `handlers.py`. To support a new Dataverse metadata block, add a new `blocks/<name>.yaml` (and a handler if needed) — see `citation.yaml` and `dataset.yaml` for examples.
  - `main.py` — orchestration, with three entry points:
    - `run_pipeline()` — the batch/cron entry point. Prints results, does not cache. Can be used with a cron job to regularly run reports for administrative purposes.
    - `fetch_metadata_report()` — single-dataset, token-based fetch (used for manual/CLI runs).
    - `run_metadata_report()` — single-dataset, used by the backend with metadata already fetched via the signed-URL flow; returns the validation result, which the backend then caches itself.

    Validation itself is delegated to the `metadig` pip package (`metadig-py`, installed straight from git), which runs the FAIR suite against check definitions from a local clone of [`NCEAS/metadig-checks`](https://github.com/NCEAS/metadig-checks.git).

**Note:** the web GUI's report cache (`backend/data/reports.db`, keyed by dataset PID) and the batch pipeline's poll checkpoint (`tools/data/reports.db`, storing only the timestamp of its last run) are separate sqlite databases used for different purposes — they are not kept in sync with each other.

### Project Layout

```
.
├── backend/                     # FastAPI web GUI (Dataverse external tool)
│   ├── data/                    # sqlite cache lives here at runtime (reports.db, gitignored)
│   ├── manifest.json            # Dataverse external tool registration
│   └── src/
│       ├── main.py              # FastAPI app + routes
│       ├── constants.py         # check name/description lookups used to render the dashboard
│       ├── static/              # report.js, styles.css served at /static
│       ├── templates/           # Jinja2 templates (empty_dashboard.html, main_dashboard.html)
│       └── utils/               # db.py (sqlite), helpers.py (Dataverse signed-URL client), templates.py (rendering)
│
├── tools/                       # `validator` package: fetch → translate → validate → cache
│   ├── data/                    # sqlite last-poll checkpoint for the batch pipeline (reports.db, gitignored)
│   ├── tmp/                     # scratch dir for intermediate XML output (contents gitignored)
│   ├── pyproject.toml           # packages `tools/src` as the `validator` package
│   └── src/validator/
│       ├── main.py              # orchestration: run_pipeline(), fetch_metadata_report(), run_metadata_report()
│       ├── retrieval/           # fetcher.py — polls Dataverse Search API for updated drafts
│       └── translation/         # translator.py, handlers.py, and blocks/*.yaml — JSON to DataCite XML mapping
│
├── .env.example                 # template for required environment variables
├── requirements.txt             # Python dependencies (see Setup)
└── README.md
```

### Pipeline

1) Metadata is retrieved either (a) via a Dataverse-signed callback URL (web GUI path), or (b) via the Dataverse Search/native API using an API token (batch pipeline path).
2) The dataset JSON is translated into Datacite XML (`tools/src/validator/translation`).
3) The Datacite XML is validated by the metadig-py engine against the FAIR suite and the `metadig-checks` definitions.
4) For the web GUI path, results are cached in sqlite and rendered on the dashboard. For the batch pipeline path, results are printed to the console (see "Running the standalone batch pipeline" below).

### Prerequisites

- Python >= 3.12
- A JVM available on your `PATH` (the `jep` dependency embeds Java to run metadig-py's Java-based checks)
- A local clone of [`NCEAS/metadig-checks`](https://github.com/NCEAS/metadig-checks.git)
- A local directory of metadig suite definition XML files (e.g. `FAIR-suite-0.5.0.xml`)
- A Dataverse instance and API token with access to the datasets you want to check

### Setup

```
git clone https://github.com/NCEAS/metadig-checks.git   # for METADIG_CHECKS_PATH
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./tools                                    # makes the `validator` package importable by backend/
cp .env.example .env
```

Then fill in `.env`:

- `SERVER_URL` — base URL of your Dataverse instance
- `API_TOKEN` — Dataverse API token (used by the batch pipeline)
- `METADIG_SUITE_PATH` — path to the directory containing your suite definition XML files
- `METADIG_CHECKS_PATH` — path to the `metadig-checks` clone from the first setup step

### Running the web GUI (Dataverse external tool)

Start the backend:

```
cd backend/src
fastapi dev
```

This serves on `http://127.0.0.1:8000`, matching the `toolUrl` in `backend/manifest.json`. Register `backend/manifest.json` with your Dataverse instance as an external tool (via Dataverse's [external tools admin API](https://guides.dataverse.org/en/latest/admin/external-tools.html)) so it appears under a dataset's **Explore** menu.

To use it: open a Dataset in Dataverse, click **Explore**, and select **metadata-checker**. The dashboard shows the dataset's title, PID, and version state; a pass/fail percentage with a progress bar; and checks grouped into Required, Recommended, and Informational columns. Each check is a click-to-flip card showing its description and output, with a visibility toggle to hide/show it from the summary. A "Re-run report" button re-fetches metadata and re-runs the validation suite.

### Running the standalone batch pipeline

```
cd tools
python3 -m src.validator.main
```

This scans the configured Dataverse root for draft datasets updated since the last run, runs the FAIR suite on each, and prints the results to the console. It does not cache reports — `tools/data/reports.db` only stores the timestamp of the last poll (see the Architecture note above).
