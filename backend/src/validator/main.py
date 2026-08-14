import json

from pathlib import Path
from xml.etree import ElementTree
from dotenv import load_dotenv

from metadig import suites
from datacite import generate_xml

load_dotenv()

SUITE_FILE = "dataverse-FAIR-suite.xml"

#note: sysmeta_path is a path to a dummy sysmeta file we don't actually need
def run_metadig_engine(suite_file):
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    metadata_path = current_dir / ".." / ".." / "tmp" / "output.xml"
    sysmeta_path = current_dir / ".." / ".." / "data" / "sysmeta_dummy.xml"
    checks_path = current_dir / "dataverse_checks" / "checks"
    path_to_suite = current_dir / "dataverse_checks" / suite_file

    result = suites.run_suite(str(path_to_suite),
                              str(checks_path),
                              str(metadata_path),
                              str(sysmeta_path)
                              )

    return result

#Parses the FAIR suite XML and returns a {check_id: level} map (e.g.
#REQUIRED/OPTIONAL/INFO), used to categorize results on the dashboard
#instead of maintaining a separate hardcoded list.
def get_check_levels():
    current_dir = Path(__file__).resolve().parent
    suite_path = current_dir / "dataverse_checks" / SUITE_FILE
    suite_doc = ElementTree.parse(str(suite_path)).getroot()
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

    result = run_metadig_engine(SUITE_FILE)

    print(result)

    return json.loads(result)
