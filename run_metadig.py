"""
run_metadig.py
--------------
Importable module that runs the metadig quality engine on a DataCite XML file.

Usage:
    from run_metadig import check
    check("path/to/datacite.xml")
"""

import subprocess
import sys
import os

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

#METADIG_PROJECT = "/home/joshuagray/metadata_checker/metadig/metadig-py"
#METADIG_CHECKS = "/home/joshuagray/metadata_checker/metadig/metadig-checks"
#_HERE = os.path.dirname(os.path.abspath(__file__))
#_METADIG_DIR = os.path.join(_HERE, "metadig")
#METADIG_PROJECT = os.path.join(_METADIG_DIR, "metadig-py")
#METADIG_CHECKS = os.path.join(_METADIG_DIR, "metadig-checks")

METADIG_PROJECT = "/path/to/metadig-py"
METADIG_CHECKS = "/path/to/metadig-checks"
METADIG_PYTHON = os.path.join(METADIG_PROJECT, ".venv", "bin", "python")
SYSMETA = "datacitesysmeta.xml"

#SUITE_PATH = os.path.join(METADIG_PROJECT, "tests", "testdata", "FAIR-suite-0.4.0.xml")
#CHECK_FOLDER = os.path.join(METADIG_PROJECT, "tests", "testdata", "checks")
#SYSMETA = os.path.join(METADIG_PROJECT, "datacitesysmeta.xml")
SP = "hashstore"

SUITE_PATH = os.path.join(METADIG_CHECKS, "src", "suites", "FAIR-suite-0.5.0.xml")
CHECK_FOLDER = os.path.join(METADIG_CHECKS, "src", "checks")

#METADIG_PROJECT  = "/home/joshuagray/metadig-py"
#METADIG_CHECKS = "/home/joshuagray/metadig-checks"
#METADIG_PYTHON   = f"{METADIG_PROJECT}/.venv/bin/python"

#SUITE_PATH   = f"{METADIG_PROJECT}/tests/testdata/FAIR-suite-0.4.0.xml"
#CHECK_FOLDER = f"{METADIG_PROJECT}/tests/testdata/checks/"
#SYSMETA      = f"{METADIG_PROJECT}/datacitesysmeta.xml"
#SP           = "hashstore"

#SUITE_PATH_2   = f"{METADIG_CHECKS}/src/suites/FAIR-suite-0.5.0.xml"
#CHECK_FOLDER_2 = f"{METADIG_CHECKS}/src/checks/"


#LICENSE_PATH   = f"{METADIG_PROJECT}/tests/testdata/checks/resource.license.present-2.0.0.xml"


#DOI_PATH   = f"{METADIG_PROJECT}/tests/testdata/checks/metadata.identifier.resolvable-2.0.0.xml"

#DATE_PATH   = f"{METADIG_PROJECT}/tests/testdata/checks/resource.publicationDate.timeframe.xml"


# ── END OF CONFIGURATION ──────────────────────────────────────────────────────

# Inline runner script — executed in a subprocess using the metadig venv's Python
_RUNNER = """
import sys, os
sys.path.insert(0, {project!r})
os.chdir({project!r})
sys.argv = {argv!r}
from metadig.metadigclient import main
main()
"""




def check(mdoc_path: str) -> None:
    """Run metadig quality checks on a DataCite XML file and print the results."""
    mdoc = os.path.abspath(mdoc_path)
    if not os.path.exists(mdoc):
        raise FileNotFoundError(f"Metadata file not found: {mdoc}")

    argv = [
        "metadigpy",
        "-runsuite",
        "-suitepath",   SUITE_PATH,
        "-checkfolder", CHECK_FOLDER,
        "-mdoc",        mdoc,
        "-sysmeta",     SYSMETA,
        "-sp",          SP,
    ]

    script = _RUNNER.format(project=METADIG_PROJECT, argv=argv)

    print(f"Running metadig checks on: {mdoc}")
    print("-" * 60)

    result = subprocess.run(
        [METADIG_PYTHON, "-c", script],
        text=True
    )

    sys.exit(result.returncode) if result.returncode != 0 else None

