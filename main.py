from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset
from pyDataverse.utils import read_file 
from pyDataverse.utils import dataverse_tree_walker
from dotenv import load_dotenv
from pyDataverse.models import Dataverse
import os
from pyDataverse.models import Datafile
import time
import argparse
import logging
import json

import subprocess
import json
import tempfile
import os

from translator.translate import translate as json_to_datacite
from translator.translate import pretty_print

from run_metadig import check




load_dotenv()
logger = logging.getLogger(__name__)

#Return (NativeAPI, DataAccessAPI) using .env credentials
def connect():
    api = NativeApi(os.getenv("SERVER_URL"), os.getenv("API_TOKEN"))
    resp = api.get_info_version()
    #print(f"Connected to Native API: {resp.json()}")
    logger.debug("User connected to Native API: %s", resp.json())
    data_api = DataAccessApi(os.getenv("SERVER_URL"))
    #print("Connected to DataAccessAPI")
    logger.debug("User connected to DataAccessAPI")
    return api, data_api


#takes in persistent identifier, returns metadata as output.json
def get_dataset_metadata(api, pid):
    #get json for draft metadata
    print(f"Getting json metadata from dataverse withh pid {pid}")
    logger.debug("Getting json metadata from dataverse withh pid %s", pid)
    resp = api.get_dataset(pid, version=':draft', auth=True, is_pid = True)
    print(json.dumps(resp.json(), indent=2))
    with open("output.json", "w") as f:
        json.dump(resp.json(), f, indent=2)

#for a published dataset (testing purposes)
def export_dataset_metadata(api, pid, export="Datacite"):
    resp = api.get_dataset_export(pid, export_format=export, auth=False)
    #print(resp.content.decode("utf-8"))
    print(type(resp))
    print(resp.text)
    with open("datacite.xml", "w") as f:
        f.write(resp.text)


def translate(in_path):
    with open(in_path) as f:
        data = json.load(f)

    root = json_to_datacite(data)
    xml_str = pretty_print(root)

    with open("output.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)
    print(xml_str)








def run_fair_checks(datacite_xml_path: str) -> dict:
    check(filename)






if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()



    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)



    api, data_api = connect()
    pid = "https://doi.org/10.5072/FK2/50K5QA"
    get_dataset_metadata(api, pid)
    translate("output.json");
    #check("output.xml")
    #check_license("output.xml")
    #check_doi("output.xml")
    #check_date("output.xml")
    check("output.xml")
    

