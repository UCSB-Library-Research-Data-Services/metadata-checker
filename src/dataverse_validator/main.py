from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset, Dataverse, Datafile
from pyDataverse.utils import read_file, dataverse_tree_walker

from xml.dom import minidom
from xml.etree import ElementTree as ET

from dotenv import load_dotenv
import os
import time
import argparse
import logging

import subprocess
import json
import tempfile

#from translator.translate import translate as json_to_datacite
#from translator.translate import pretty_print

#from run_metadig import check

from retrieval import fetch
from translation import translate, pretty_print

from metadig import checks
from metadig import suites

from pathlib import Path


logger = logging.getLogger(__name__)
load_dotenv()
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
    #print(json.dumps(resp.json(), indent=2))
    #with open("output.json", "w") as f:
        #json.dump(resp.json(), f, indent=2)
    return resp.json()

#for a published dataset (testing purposes)
def export_dataset_metadata(api, pid, export="Datacite"):
    resp = api.get_dataset_export(pid, export_format=export, auth=False)
    #print(resp.content.decode("utf-8"))
    print(type(resp))
    print(resp.text)
    with open("datacite.xml", "w") as f:
        f.write(resp.text)


"""
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
"""

#note: sysmeta_path is a path to a dummy sysmeta file we don't actually need
def run_metadig_engine(suite_file):
    path_to_suite = Path(os.environ.get("METADIG_SUITE_PATH")) / suite_file


    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    metadata_path = current_dir / ".." / ".." / "tmp" / "output.xml"

    current_dir = current_file.parent
    sysmeta_path = current_dir / ".." / ".." / "data" / "sysmeta_dummy.xml"

    result = suites.run_suite(str(path_to_suite),
                              str(os.environ.get("METADIG_CHECKS_PATH")),
                              str(metadata_path),
                              str(sysmeta_path)
                              )
    
    return result

def write_xml(xml_str):
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent

    target_folder = current_dir / ".." / ".." / "tmp" / "output.xml"


    with open(target_folder, "w", encoding="utf-8") as f:
        f.write(xml_str)





if __name__ == "__main__":

    api, data_api = connect()

    dataverse_url = os.environ.get("SERVER_URL")
    api_token = os.environ.get("API_TOKEN")

    dataset_pids = fetch("ucsb", dataverse_url, api_token)

    if dataset_pids is None:
        print("No new updated datasets")
    else:
        for pid in dataset_pids:
            metadata = get_dataset_metadata(api, pid)
            root = translate(metadata)
            xml_str = pretty_print(root)
            print(xml_str)
            write_xml(xml_str)
            result = run_metadig_engine("FAIR-suite-0.5.0.xml")
            print(result)
    #print(get_dataset_metadata(api, pid))
    #translate("output.json");
    #check("output.xml")

    

