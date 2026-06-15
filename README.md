## Metadata Validation Tool
Joshua Gray

### Summary

This is a python script that is used to validate metadata from datasets in the Dataverse repository system.

### Pipeline

1) The metadata is downloaded from an unpublished dataset as json
2) A translation tool translates the json into a Datacite XML file, which will be used for the validation
3) The py-metadig engine is used to validate the Datacite XML file

### Setup and Usage


Create a .env file following the .env.example

Create a virtual environment with `python3 -m venv .venv` and do `pip install -r requirements.txt`

Inside of `main.py` on line 111, set the doi for the dataset you want to download.

Inside of `run_metadig.py`, change lines 24 and 25 to be the paths to the metadig-py and metadig-checks repositories.

These repositories and setup instructions can be found here: 
https://github.com/UCSB-Library-Research-Data-Services/metadig-py
https://github.com/NCEAS/metadig-checks.git

Run `python3 main.py`

