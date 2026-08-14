## Metadata Validation Tool
Joshua Gray

### Summary

This is a metadata validation tool for the Dataverse academic repository system, and provides infrastructure for using the [metadig-py](https://github.com/UCSB-Library-Research-Data-Services/metadig-py/tree/master) metadata validation tool on the metadata for a given Dataset. Currently, the tool runs a suite of checks corresponding to FAIR data principles.

The application provides a web GUI for running and viewing the metadig reports, which is accessed in the form of an external tool in Dataverse.

### Architecture

- **`backend/`** — a FastAPI app (`backend/src/main.py`) that Dataverse launches as an "external tool", registered via `backend/manifest.json` and shown under a dataset's **Explore** menu. Routes:
  - `GET /metadata-report` — the landing page Dataverse opens. It receives a base64-encoded `callback` query param from Dataverse, decodes it to fetch the dataset's metadata via Dataverse's signed-URL mechanism (`backend/src/utils/helpers.py`), and renders either `empty_dashboard.html` (no cached report yet) or `main_dashboard.html` (a cached report exists), backed by a sqlite cache (`backend/src/utils/db.py`, `backend/data/reports.db`). The frontend templates are rendered server-side using jinja2.
  - `POST /api/load-new-report` — re-fetches metadata for a dataset and re-runs the validator, caching the new report in the database.
  - `POST /api/toggle-check-visibility` — toggles whether a given check is shown on the dashboard at the discretion of the user.
  - `POST /api/send-report-email` — emails a cached report to a user-supplied address (see `backend/EMAIL_REPORT.md` for the full flow).

- **`backend/src/validator/`** — a local (not separately installed) package that turns a dataset's metadata into a FAIR validation report:
  - `run_metadata_report(metadata)` — translates the metadata into DataCite XML via the external [`dataverse-datacite-translator`](https://github.com/UCSB-Library-Research-Data-Services/dataverse-datacite-translator) package, then hands it to `run_metadig_engine()`.
  - `run_metadig_engine(suite_file)` — runs the `metadig-py` engine (`metadig` pip package, installed straight from git) against the FAIR suite and check definitions from a local clone of [`NCEAS/metadig-checks`](https://github.com/NCEAS/metadig-checks.git), filtering out any check that errors out (status `ERROR`, as opposed to a genuine `FAILURE`) and logging which ones were dropped.

### Project Layout

```
.
├── backend/                     # FastAPI web GUI (Dataverse external tool)
│   ├── data/                    # sqlite cache (reports.db, gitignored) + sysmeta_dummy.xml
│   ├── tmp/                     # scratch dir for intermediate XML output (contents gitignored)
│   ├── manifest.json            # Dataverse external tool registration
│   ├── EMAIL_REPORT.md          # email-a-report feature: architecture + flow
│   └── src/
│       ├── main.py              # FastAPI app + routes
│       ├── constants.py         # check name/description lookups used to render the dashboard
│       ├── static/              # report.js, styles.css served at /static
│       ├── templates/           # Jinja2 templates (empty_dashboard.html, main_dashboard.html, email_report.html)
│       ├── utils/               # db.py (sqlite), helpers.py (Dataverse signed-URL client), templates.py (rendering), mailer.py (SMTP)
│       └── validator/           # main.py — run_metadata_report(), run_metadig_engine()
│
├── .env.example                 # template for required environment variables
├── requirements.txt             # Python dependencies (see Setup)
└── README.md
```

### Pipeline

1) Metadata is retrieved via a Dataverse-signed callback URL.
2) The dataset JSON is translated into DataCite XML by the external [`dataverse-datacite-translator`](https://github.com/UCSB-Library-Research-Data-Services/dataverse-datacite-translator) package.
3) The DataCite XML is validated by the metadig-py engine against the FAIR suite and the `metadig-checks` definitions, and any check that errors out (as opposed to genuinely failing) is filtered from the results.
4) Results are cached in sqlite and rendered on the dashboard.

### Prerequisites

- Python >= 3.12
- A JVM available on your `PATH` (the `jep` dependency embeds Java to run metadig-py's Java-based checks)
- A local clone of [`NCEAS/metadig-checks`](https://github.com/NCEAS/metadig-checks.git)
- A local directory of metadig suite definition XML files (e.g. `FAIR-suite-0.5.0.xml`)
- A Dataverse instance registered to launch this app as an external tool

### Setup

```
git clone https://github.com/NCEAS/metadig-checks.git   # for METADIG_CHECKS_PATH
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then fill in `.env`:

- `METADIG_SUITE_PATH` — path to the directory containing your suite definition XML files
- `METADIG_CHECKS_PATH` — path to the `metadig-checks` clone from the first setup step

### Running the web GUI (Dataverse external tool)

Start the backend:

```
cd backend/src
fastapi dev
```

This serves on `http://127.0.0.1:8000`, matching the `toolUrl` in `backend/manifest.json`. Register `backend/manifest.json` with your Dataverse instance as an external tool (via Dataverse's [external tools admin API](https://guides.dataverse.org/en/latest/admin/external-tools.html)) so it appears under a dataset's **Explore** menu.

To use it: open a Dataset in Dataverse, click **Explore**, and select **metadata-checker**. The dashboard shows the dataset's title, PID, and version state; a pass/fail percentage with a progress bar; and checks grouped into Required, Recommended, and Informational columns. Each check is a click-to-flip card showing its description and output, with a visibility toggle to hide/show it from the summary. A "Re-run report" button re-fetches metadata and re-runs the validation suite, and a "Send me a report" button emails the cached report to an address you supply.
