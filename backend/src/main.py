from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from validator import fetch_metadata_report, run_metadata_report
from jinja2 import Environment, PackageLoader, select_autoescape
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import base64
from typing import Optional
import httpx

import json
from pydantic import BaseModel

class RefreshBody(BaseModel):
    dataset_pid: str
    callback: str


import sqlite3

BASE_DIR = Path(__file__).resolve().parent

env = Environment(
        loader=PackageLoader("main"),
        autoescape=select_autoescape()
    )

template = env.get_template("mytemplate.html")
empty_dashboard = env.get_template("empty_dashboard.html")

app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

DB_NAME = "reports.db"


REQUIRED_CHECKS_NAMES = {
    'entity.attributeDefinition.present-2.1.0',
    'entity.attributeDefinition.sufficient-2.1.0',
    'entity.attributeDomain.present-2.0.0',
    'entity.attributeName.differs-2.1.0',
    'entity.attributeNames.unique-2.1.0',
    'entity.attributeEnumeratedDomains.present.1',
    'entity.checksum.present-2.1.0',
    'entity.description.present-2.1.0',
    'entity.distributionURL.resolvable-2.1.0',
    'entity.format.nonproprietary-2.1.0',
    'entity.format.present-2.1.0',
    'entity.identifier.present-2.1.0',
    'entity.name.present-2.1.0',
    'entity.qualityDescription.present.1',
    'entity.attributeUnits.present-2.1.0',
    'metadata.identifier.present-2.1.0',
    'metadata.identifier.resolvable-2.1.0',
    'provenance.ProcessStepCode.present-2.1.0',
    'provenance.sourceEntity.present-2.0.0',
    'provenance.trace.present-2.0.0',
    'resource.abstractLength.sufficient-2.0.0',
    'resource.accessControlRules.present-2.0.0',
    'resource.creator.present-2.0.0',
    'resource.creatorIdentifier.present-2.1.0',
    'resource.distributionContact.present-2.1.0',
    'resource.distributionContactIdentifier.present-2.1.0',
    'resource.keywords.present-2.1.0',
    'resource.landingPage.present-2.1.0',
    'resource.license.present-2.1.0',
    'resource.methods.present-2.0.0',
    'resource.publicationDate.present-2.1.0',
    'resource.publisher.present-2.1.0',
    'resource.titleLength.sufficient-2.0.0'
}

INFORMATION_CHECKS_NAMES = {
    'resource.type.valid-2.0.0'
}

OPTIONAL_CHECKS_NAMES = {
    'entity.attributeCoverageContentType.present-2.0.0',
    'entity.attributeMeasurementScale.present-2.0.0',
    'entity.attributePrecision.present-2.0.0',
    'entity.attributeStorageType.present-2.0.0',
    'entity.identifierType.present-2.1.0',
    'entity.type.present.1',
    'geographic.description.present-2.0.0',
    'resource.keywordType.present-2.1.0',
    'resource.keywords.controlled-2.1.0',
    'resource.publicationDate.timeframe-2.0.0',
    'resource.publisherIdentifier.present-2.1.0',
    'resource.revisionDate.present-2.0.0',
    'resource.serviceLocation.present-2.0.0',
    'resource.serviceProvider.present-2.1.0',
    'resource.serviceType.present-2.0.0',
    'resource.spatialExtent.present-2.0.0',
    'resource.taxonomicExtent.present.1',
    'resource.temporalExtent.present-2.0.0'
}


HUMAN_READABLE_NAMES = {
    # === Findable Checks ===
    'resource.abstractLength.sufficient-2.0.0': 'Sufficient Abstract Length',
    'resource.type.valid-2.0.0': 'Valid Resource Type',
    'resource.keywords.controlled-2.1.0': 'Controlled Vocabulary Keywords',
    'resource.keywords.present-2.1.0': 'Keywords Presence',
    'resource.keywordType.present-2.1.0': 'Keyword Type Specified',
    'resource.publicationDate.timeframe-2.0.0': 'Valid Publication Date Timeframe',
    'metadata.identifier.present-2.1.0': 'Metadata Identifier Presence',
    'resource.creator.present-2.0.0': 'Creator Information Presence',
    'resource.creatorIdentifier.present-2.1.0': 'Creator Persistent Identifier Presence',
    'resource.revisionDate.present-2.0.0': 'Revision Date Presence',
    'entity.identifier.present-2.1.0': 'Data Entity Identifier Presence',
    'entity.identifierType.present-2.1.0': 'Data Entity Identifier Type Specified',
    'resource.publicationDate.present-2.1.0': 'Publication Date Presence',
    'resource.titleLength.sufficient-2.0.0': 'Sufficient Title Length',
    'resource.spatialExtent.present-2.0.0': 'Spatial Extent/Bounding Box Presence',
    'geographic.description.present-2.0.0': 'Geographic Description Presence',
    'resource.taxonomicExtent.present.1': 'Taxonomic Coverage Presence',
    'resource.temporalExtent.present-2.0.0': 'Temporal Extent/Date Range Presence',

    # === Accessible Checks ===
    'resource.accessControlRules.present-2.0.0': 'Access Control Rules Defined',
    'resource.landingPage.present-2.1.0': 'Resource Landing Page Presence',
    'resource.distributionContact.present-2.1.0': 'Distribution Contact Presence',
    'resource.distributionContactIdentifier.present-2.1.0': 'Distribution Contact Identifier Presence',
    'metadata.identifier.resolvable-2.1.0': 'Resolvable Metadata Identifier (URL/DOI)',
    'resource.publisher.present-2.1.0': 'Publisher Information Presence',
    'resource.publisherIdentifier.present-2.1.0': 'Publisher Identifier Presence',
    'resource.serviceLocation.present-2.0.0': 'Service Location URL Presence',
    'resource.serviceProvider.present-2.1.0': 'Service Provider Presence',
    'entity.distributionURL.resolvable-2.1.0': 'Resolvable Data Download URL',

    # === Interoperable Checks ===
    'entity.attributeName.differs-2.1.0': 'Attribute Names Differ from Table Headers',
    'entity.attributeNames.unique-2.1.0': 'Unique Column/Attribute Names',
    'entity.attributeDefinition.present-2.1.0': 'Attribute/Column Definitions Presence',
    'entity.attributeDefinition.sufficient-2.1.0': 'Sufficient Attribute Definition Detail',
    'entity.attributeStorageType.present-2.0.0': 'Data Storage Type Specified',
    'entity.checksum.present-2.1.0': 'File Checksum/Hash Presence',
    'entity.attributeCoverageContentType.present-2.0.0': 'Attribute Coverage Content Type Specified',
    'entity.attributeEnumeratedDomains.present.1': 'Enumerated Domain/Code Definitions Presence',
    'entity.format.present-2.1.0': 'File Format Specified',
    'entity.name.present-2.1.0': 'Data Entity/File Name Presence',
    'entity.type.present.1': 'Data Entity Type Specified',
    'resource.serviceType.present-2.0.0': 'Service Type Specified',
    
    # === Reusable Checks ===
    'entity.format.nonproprietary-2.1.0': 'Non-Proprietary File Format',
    'entity.attributeDomain.present-2.0.0': 'Attribute Domain/Data Range Presence',
    'entity.attributeUnits.present-2.1.0': 'Attribute Measurement Units Presence',
    'entity.attributeMeasurementScale.present-2.0.0': 'Measurement Scale Specified',
    'entity.attributePrecision.present-2.0.0': 'Measurement Precision Specified',
    'entity.description.present-2.1.0': 'Data Entity/File Description Presence',
    'entity.qualityDescription.present.1': 'Data Quality Description Presence',
    'resource.methods.present-2.0.0': 'Methodology/Sampling Protocol Presence',
    'provenance.ProcessStepCode.present-2.1.0': 'Provenance Proven Process Step Code Presence',
    'provenance.sourceEntity.present-2.0.0': 'Provenance Source Entity Specified',
    'provenance.trace.present-2.0.0': 'Provenance Traceability Presence',
    'resource.license.present-2.1.0': 'Data License/Usage Terms Presence'
}

def get_description(metadata):
    fields = metadata['data']['latestVersion']['metadataBlocks']['citation']['fields']
    description_field = next((f for f in fields if f['typeName'] == 'dsDescription'), None)
    if description_field:
        return description_field['value'][0]['dsDescriptionValue']['value']
    return "No description found"

def get_title(metadata):
    fields = metadata['data']['latestVersion']['metadataBlocks']['citation']['fields']
    title_field = next((f for f in fields if f['typeName'] == 'title'), None)
    if title_field:
        return title_field['value']
    return "No title found"

def get_version_state(metadata):
    return metadata['data']['latestVersion']['versionState']

def get_persistent_id(metadata):
    return metadata['data']['identifier']




async def get_metadata(callback):
    decoded_url = base64.b64decode(callback).decode("utf-8")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(decoded_url)
            res.raise_for_status()
            json_manifest = res.json()           
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Dataverse callback failed")

    signed_urls = json_manifest['data']['signedUrls']
    metadata_api_request = next((call for call in signed_urls if call['name'] == 'retrieveDatasetMetadata'), None)

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(metadata_api_request['signedUrl'])
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Metadata retreival failed")


async def get_json(callback):
    decoded_url = base64.b64decode(callback).decode("utf-8")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(decoded_url)
            res.raise_for_status()
            return res.json()
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Dataverse callback failed")




async def render_dashboard(metadata, validation_report):

    status = validation_report["run_status"]
    test_results = validation_report["results"]

    #seperate out into three categories
    required_tests = []
    optional_tests = []
    information_tests = []


    #used for stats
    passed_checks = 0
    passed_required = 0
    passed_optional = 0
    passed_information = 0



    #sort into three lists, get stats
    for test in test_results:
        if test['check_id'].removesuffix('.xml') in REQUIRED_CHECKS_NAMES:
            required_tests.append({'check_id': HUMAN_READABLE_NAMES[test['check_id'].removesuffix('.xml')],
                                   'status': test['status']
                                   })

            if test['status'] == 'SUCCESS':
                passed_required += 1

        if test['check_id'].removesuffix('.xml') in OPTIONAL_CHECKS_NAMES:
            optional_tests.append({'check_id': HUMAN_READABLE_NAMES[test['check_id'].removesuffix('.xml')],
                                   'status': test['status']
                                   })
            if test['status'] == 'SUCCESS':
                passed_optional += 1

        if test['check_id'].removesuffix('.xml') in INFORMATION_CHECKS_NAMES:
            information_tests.append({'check_id': HUMAN_READABLE_NAMES[test['check_id'].removesuffix('.xml')],
                                   'status': test['status']
                                   })
            if test['status'] == 'SUCCESS':
                passed_information += 1

        if test['status'] == 'SUCCESS':
            passed_checks += 1



    description = get_description(metadata)
    title = get_title(metadata)
    version_state = get_version_state(metadata)
    persistent_id = get_persistent_id(metadata)



    return template.render(dataset_id=persistent_id,
                           status=status,
                           required_tests = required_tests, 
                           optional_tests = optional_tests,
                           information_tests = information_tests,
                           dataset_title = title,
                           version_state = version_state,
                           passed_checks = passed_checks/len(test_results),
                           passed_required = passed_required,
                           total_required = len(required_tests),
                           passed_optional = passed_optional,
                           total_optional = len(optional_tests),
                           passed_information = passed_information,
                           total_information = len(information_tests)
                           )
    

#Connect to sqlite3 database and initialize datasets table, returns connection
def connect_to_database():

    current_dir = Path(__file__).resolve().parent

    db_path  = current_dir/ ".." / "data" / DB_NAME

    conn = sqlite3.connect(str(db_path))

    cursor = conn.cursor()

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS datasets(
                        dataset_id TEXT,
                        metadata TEXT NOT NULL,
                        report TEXT NOT NULL,
                        PRIMARY KEY(dataset_id))
                    """)


    return conn



#takes in metadata and metadata report, caches it into the sqlite database
def cache_report(conn, dataset_id, metadata, report):
    #initialize database if not already
    cursor = conn.cursor()

    #check if we already have a report cached in the database

    cursor.execute("""
                    SELECT *
                    FROM datasets
                    WHERE dataset_id = ?
                    """,
                   (dataset_id,)
                   )

    if cursor.fetchone() is None:
        #insert report into database
        cursor.execute("""
                        INSERT INTO datasets (dataset_id, metadata, report)
                        VALUES (?, ?, ?)
                        """,
                       (dataset_id, json.dumps(metadata), json.dumps(report))
                       )
    else:
        #update already existing dataset
        cursor.execute("""
                        UPDATE datasets
                        SET metadata = ?,
                            report = ?,
                        WHERE dataset_id = ?
                        """,
                       (json.dumps(report), json.dumps(dataset_id))
                       )

    conn.commit()
    print(f"Succesfully cached database report")


#Takes in a dataset id
#If there exists a report, returns a tuple of (metadata, report)
#Otherwise returns None
def fetch_cached_report(conn, dataset_id):

    cursor = conn.cursor()

    cursor.execute("""
                    SELECT *
                    FROM datasets
                    WHERE dataset_id = ?
                    """,
                   (dataset_id,)
                   )

    row = cursor.fetchone()

    if row is None:
        return None

    return (json.loads(row[1]), json.loads(row[2]))







@app.get("/")
async def root():
    #return template.render(name_variable="josh")
    return {"Status":"Succesfully connected"}

@app.get("/metadata-report", response_class=HTMLResponse)
async def get_metadata_report( callback:str, locale: str):
    #metadata = await get_metadata(callback)
    #validation_report = await run_metadata_report(metadata)

    conn = connect_to_database()

    callback_response = await get_json(callback)

    if callback_response:
        dataset_pid = callback_response['data']['queryParameters']['datasetPid']

    else:
        dataset_pid = None


    cached_report_info = fetch_cached_report(conn, dataset_pid)
    if cached_report_info is None:
        return empty_dashboard.render(dataset_id=dataset_pid, callback=callback)

    metadata, validation_report = cached_report_info 
    return await render_dashboard(metadata, validation_report)




@app.post("/api/load-new-report")
async def load_new_report(refreshBody: RefreshBody):
    metadata = await get_metadata(refreshBody.callback)
    validation_report = await run_metadata_report(metadata)

    conn = connect_to_database()

    cache_report(conn, refreshBody.dataset_pid, metadata, validation_report)

    #return await render_dashboard(metadata, validation_report)

    return {"message":"succesfully ran and cached new report"}


