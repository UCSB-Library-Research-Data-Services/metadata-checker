import json
import os

from pathlib import Path
from xml.etree import ElementTree
from dotenv import load_dotenv

from metadig import suites
from datacite import generate_xml

load_dotenv()

DATAVERSE_CHECKS_DIR = Path(__file__).resolve().parent / "dataverse_checks"

#Both overridable via .env; fall back to the bundled dataverse_checks/ files
#when unset. Override values should be absolute paths - a relative one would
#resolve against whatever cwd the FastAPI process happens to start from.
SUITE_PATH = Path(os.getenv("METADIG_SUITE_PATH", str(DATAVERSE_CHECKS_DIR / "dataverse-FAIR-suite.xml")))
CHECKS_PATH = Path(os.getenv("METADIG_CHECKS_PATH", str(DATAVERSE_CHECKS_DIR / "checks")))


#note: sysmeta_path is a path to a dummy sysmeta file we don't actually need
def run_metadig_engine():
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    metadata_path = current_dir / ".." / ".." / "tmp" / "output.xml"
    sysmeta_path = current_dir / ".." / ".." / "data" / "sysmeta_dummy.xml"

    result = suites.run_suite(str(SUITE_PATH),
                              str(CHECKS_PATH),
                              str(metadata_path),
                              str(sysmeta_path)
                              )

    return result

#Parses the FAIR suite XML and returns a {check_id: level} map (e.g.
#REQUIRED/OPTIONAL/INFO), used to categorize results on the dashboard
#instead of maintaining a separate hardcoded list.
def get_check_levels():
    suite_doc = ElementTree.parse(str(SUITE_PATH)).getroot()
    return {
        check.find("id").text.strip(): check.find("level").text.strip()
        for check in suite_doc.findall("check")
    }

#Runs report based on a metadata retrieved by a signed URL, used by FastAPI
#Takes in metadata, returns metadig report
async def run_metadata_report(metadata):
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    target_folder = current_dir / ".." / ".." / "tmp" / "output.xml"

    generate_xml(metadata, target_folder)

    result = run_metadig_engine()

    print(result)

    return json.loads(result)
