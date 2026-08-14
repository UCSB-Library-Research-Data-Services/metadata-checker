import os
import json
import logging

from pathlib import Path
from dotenv import load_dotenv

from metadig import suites
from datacite import generate_xml

logger = logging.getLogger(__name__)
load_dotenv()

#note: sysmeta_path is a path to a dummy sysmeta file we don't actually need
def run_metadig_engine(suite_file):
    path_to_suite = Path(os.environ.get("METADIG_SUITE_PATH")) / suite_file

    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    metadata_path = current_dir / ".." / ".." / "tmp" / "output.xml"
    sysmeta_path = current_dir / ".." / ".." / "data" / "sysmeta_dummy.xml"
    checks_path = current_dir / "dataverse_checks"

    result = suites.run_suite(str(path_to_suite),
                              str(checks_path),
                              str(metadata_path),
                              str(sysmeta_path)
                              )

    suite_results = json.loads(result)

    errored_checks = [r["check_id"] for r in suite_results["results"] if r["status"] == "ERROR"]
    if errored_checks:
        logger.warning("Filtered out checks that errored while running: %s", errored_checks)

    suite_results["results"] = [r for r in suite_results["results"] if r["status"] != "ERROR"]

    return json.dumps(suite_results, indent=4)

#Runs report based on a metadata retrieved by a signed URL, used by FastAPI
#Takes in metadata, returns metadig report
async def run_metadata_report(metadata):
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    target_folder = current_dir / ".." / ".." / "tmp" / "output.xml"

    generate_xml(metadata, target_folder)

    result = run_metadig_engine("FAIR-suite-0.5.0.xml")

    return json.loads(result)
