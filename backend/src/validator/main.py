import os
import json

from pathlib import Path
from dotenv import load_dotenv

from metadig import suites
from datacite import generate_xml

load_dotenv()

#note: sysmeta_path is a path to a dummy sysmeta file we don't actually need
def run_metadig_engine(suite_file):
    path_to_suite = Path(os.environ.get("METADIG_SUITE_PATH")) / suite_file

    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    metadata_path = current_dir / ".." / ".." / "tmp" / "output.xml"
    sysmeta_path = current_dir / ".." / ".." / "data" / "sysmeta_dummy.xml"

    result = suites.run_suite(str(path_to_suite),
                              str(os.environ.get("METADIG_CHECKS_PATH")),
                              str(metadata_path),
                              str(sysmeta_path)
                              )

    return result

#Runs report based on a metadata retrieved by a signed URL, used by FastAPI
#Takes in metadata, returns metadig report
async def run_metadata_report(metadata):
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    target_folder = current_dir / ".." / ".." / "tmp" / "output.xml"

    generate_xml(metadata, target_folder)

    result = run_metadig_engine("FAIR-suite-0.5.0.xml")

    return json.loads(result)
