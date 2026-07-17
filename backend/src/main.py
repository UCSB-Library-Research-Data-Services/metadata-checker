from fastapi import FastAPI, HTTPException
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
import sqlite3


class RefreshBody(BaseModel):
    dataset_pid: str
    callback: str

class ChecksToToggle(BaseModel):
    checks: list[str]



BASE_DIR = Path(__file__).resolve().parent

env = Environment(
        loader=PackageLoader("main"),
        autoescape=select_autoescape()
    )

main_dashboard = env.get_template("main_dashboard.html")
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


CHECK_DESCRIPTIONS = {
    # === Findable Checks ===
    'resource.abstractLength.sufficient-2.0.0': "Confirms the dataset has an abstract that is long enough to meaningfully summarize the data. A substantive abstract lets people judge whether a dataset is relevant to their work without downloading it first, which is central to making data Findable.",
    'resource.type.valid-2.0.0': "Checks that the dataset declares a recognized resource type (e.g. dataset, software, collection). A valid, controlled resource type helps search systems and catalogs correctly classify and surface the dataset.",
    'resource.keywords.controlled-2.1.0': "Checks whether the dataset's keywords are drawn from a controlled vocabulary or thesaurus rather than free text. Controlled keywords make search and cross-dataset discovery far more reliable than ad hoc terms.",
    'resource.keywords.present-2.1.0': "Confirms that the dataset has at least one keyword. Keywords are one of the primary ways search engines and repositories index and surface datasets to potential users.",
    'resource.keywordType.present-2.1.0': "Checks that each keyword is labeled with a type (e.g. subject, place, taxonomic). Typed keywords let search systems facet and filter more precisely than untyped free-text tags.",
    'resource.publicationDate.timeframe-2.0.0': "Verifies that the dataset's publication date is not set in the future. An implausible publication date undermines trust in the record and can break date-based search and sorting.",
    'metadata.identifier.present-2.1.0': "Confirms the metadata record itself has a persistent identifier (such as a DOI). Without one, the record can't be reliably cited, linked to, or tracked over time.",
    'resource.creator.present-2.0.0': "Checks that at least one creator (author) is listed for the dataset. Creator information is essential for attribution, citation, and letting users find related work by the same author.",
    'resource.creatorIdentifier.present-2.1.0': "Checks that a listed creator has a persistent identifier, such as an ORCID. This disambiguates authors with similar names and links the dataset to the creator's other work.",
    'resource.revisionDate.present-2.0.0': "Confirms a revision or creation date is recorded for the dataset. This date helps users judge how current the data is and supports version tracking over time.",
    'entity.identifier.present-2.1.0': "Checks that each data entity (file/table) within the dataset has its own identifier. Entity-level identifiers make it possible to reference and cite individual files, not just the dataset as a whole.",
    'entity.identifierType.present-2.1.0': "Checks that each entity identifier declares what type of identifier it is (e.g. DOI, URL, UUID). Knowing the identifier type lets tools correctly resolve or interpret it.",
    'resource.publicationDate.present-2.1.0': "Confirms the dataset has a publication date recorded. A publication date is required for proper citation and for search systems that sort or filter by recency.",
    'resource.titleLength.sufficient-2.0.0': "Checks that the dataset title is neither too short to be descriptive nor so long that it becomes unwieldy (roughly 7–20 words). A well-sized title helps users quickly judge relevance in search results.",
    'resource.spatialExtent.present-2.0.0': "Checks that the dataset records at least one spatial extent (e.g. a bounding box). Spatial extent lets users find datasets covering a geographic area of interest through map-based or location search.",
    'geographic.description.present-2.0.0': "Confirms the dataset includes a plain-language description of its geographic coverage. This gives context to the raw coordinates and helps non-technical users understand where the data was collected.",
    'resource.taxonomicExtent.present.1': "Checks that the dataset records the taxonomic coverage (the species or taxa involved), where relevant. Taxonomic metadata lets researchers find datasets about specific organisms or taxonomic groups.",
    'resource.temporalExtent.present-2.0.0': "Checks that the dataset records the time period the data covers. Temporal extent is essential for finding datasets relevant to a particular date range or study period.",

    # === Accessible Checks ===
    'resource.accessControlRules.present-2.0.0': "Confirms that access control rules are explicitly defined for the dataset. Explicit access rules make clear who can view or download the data, rather than leaving access ambiguous.",
    'resource.landingPage.present-2.1.0': "Checks that the dataset has a working landing page URL. A resolvable landing page gives users a stable, human-readable entry point to view and access the dataset.",
    'resource.distributionContact.present-2.1.0': "Checks that a contact person or organization is listed for questions about accessing the data. This gives users someone to reach if the data can't be retrieved or if they have access questions.",
    'resource.distributionContactIdentifier.present-2.1.0': "Checks that the listed distribution contact has a persistent identifier (such as an ORCID or ROR ID). This disambiguates the contact and links them to other records.",
    'metadata.identifier.resolvable-2.1.0': "Checks that the metadata record's persistent identifier (e.g. a DOI) actually resolves to a live page. An identifier that exists but doesn't resolve breaks citation and long-term accessibility.",
    'resource.publisher.present-2.1.0': "Verifies that the dataset metadata records a publisher — the organization or repository responsible for making the dataset available. Publisher information supports proper citation and helps users judge the authority of the resource.",
    'resource.publisherIdentifier.present-2.1.0': "Checks that the publisher is identified with a persistent identifier (such as a ROR ID). This disambiguates the publishing organization from others with similar names.",
    'resource.serviceLocation.present-2.0.0': "Checks that a service location URL is present when the dataset is exposed via a data service (e.g. a web service or API). This tells users and machines where to actually query the service.",
    'resource.serviceProvider.present-2.1.0': "Checks that the provider of a data service is identified. Knowing the service provider helps users judge the reliability and support available for programmatic access.",
    'entity.distributionURL.resolvable-2.1.0': "Checks that each data file's download URL actually resolves rather than returning an error. A broken distribution URL means the underlying data can't be retrieved even though the dataset record exists.",

    # === Interoperable Checks ===
    'entity.attributeName.differs-2.1.0': "Checks that each attribute's definition is a real explanation and not just a restatement of its column name. A definition that merely repeats the name gives readers no additional information about what the column actually contains.",
    'entity.attributeNames.unique-2.1.0': "Checks that no two attributes (columns/variables) within a data entity share the same name. Duplicate attribute names make it impossible to unambiguously map a metadata description to the correct column, undermining reliable reuse of the data.",
    'entity.attributeDefinition.present-2.1.0': "Checks that every attribute (column/variable) has an accompanying definition. Without a definition, users have to guess what a column represents from its name alone.",
    'entity.attributeDefinition.sufficient-2.1.0': "Checks that attribute definitions are detailed enough to be useful, not just a word or two. A definition needs enough substance to actually explain what the attribute measures or represents.",
    'entity.attributeStorageType.present-2.0.0': "Checks that each attribute specifies its storage type (e.g. string, integer, float, date). Knowing the storage type lets software correctly parse and validate the underlying data values.",
    'entity.checksum.present-2.1.0': "Checks that each data file has a checksum and the algorithm used to generate it (e.g. MD5, SHA-256). Checksums let users verify a downloaded file is complete and unmodified from the original.",
    'entity.attributeCoverageContentType.present-2.0.0': "Checks that each attribute specifies its coverage content type (e.g. whether it's a physical measurement, a quality flag, or an auxiliary variable). This classification helps software and users interpret what role the attribute plays in the data.",
    'entity.attributeEnumeratedDomains.present.1': "Checks that attributes with a fixed, limited set of valid values (e.g. codes or categories) have that enumerated domain explicitly defined. Without it, users can't know which coded values are valid or what they mean.",
    'entity.format.present-2.1.0': "Checks that each data file declares its file format (e.g. CSV, NetCDF). Format information is required for software to know how to open and parse the file correctly.",
    'entity.name.present-2.1.0': "Checks that every data entity (file/table) has a name. A name lets users distinguish between multiple files in a dataset and understand what each one contains at a glance.",
    'entity.type.present.1': "Checks that each data entity specifies its type (e.g. tabular data, image, other). Entity type helps software and users route the file to the right viewer or processing tool.",
    'resource.serviceType.present-2.0.0': "Checks that a data service declares its service type (e.g. WMS, WFS, OPeNDAP). Knowing the service type tells client software which protocol to use to query it.",

    # === Reusable Checks ===
    'entity.format.nonproprietary-2.1.0': "Checks that data files are published in open, non-proprietary formats (e.g. CSV instead of a vendor-specific binary format). Open formats can be read without proprietary software, maximizing long-term reuse.",
    'entity.attributeDomain.present-2.0.0': "Checks that each attribute's valid range or domain of values is documented (e.g. numeric bounds, allowed categories). A defined domain lets users validate the data and understand its limits.",
    'entity.attributeUnits.present-2.1.0': "Checks that attributes representing measurements declare their units (e.g. meters, °C). Without units, a numeric value is ambiguous and effectively unusable for analysis.",
    'entity.attributeMeasurementScale.present-2.0.0': "Checks that each attribute specifies its measurement scale (nominal, ordinal, interval, or ratio). Knowing the measurement scale tells analysts which statistical operations are valid to apply.",
    'entity.attributePrecision.present-2.0.0': "Checks that attributes representing measurements declare their precision. Precision tells users how much confidence to place in a value's exactness before drawing conclusions from it.",
    'entity.description.present-2.1.0': "Checks that every data entity (file/table) has a description explaining its contents. An entity-level description helps users understand a specific file without having to infer its purpose from the filename alone.",
    'entity.qualityDescription.present.1': "Checks that the dataset documents the quality-control practices and protocols used to produce the data. This context lets reusers judge how much confidence to place in the data for their own purposes.",
    'resource.methods.present-2.0.0': "Checks that the dataset includes a detailed methods or sampling protocol section. Documented methods let others assess, replicate, or properly reuse the data in their own research.",
    'provenance.ProcessStepCode.present-2.1.0': "Checks that processing steps applied to the data specify the software or code used. This lets others trace exactly how raw data was transformed into the published product.",
    'provenance.sourceEntity.present-2.0.0': "Checks that derived data entities identify their source entity in the provenance chain. This traceability lets users follow a data product back to the original inputs it was derived from.",
    'provenance.trace.present-2.0.0': "Checks that the dataset includes provenance information describing how the data was produced or derived. Provenance is key to trusting and correctly reusing data that has gone through processing steps.",
    'resource.license.present-2.1.0': "Checks that the dataset specifies a usage license (e.g. CC-BY, CC0). Without an explicit license, other researchers can't be sure what they're legally permitted to do with the data.",
}

def get_description(metadata):
    fields = metadata.get('data', {}).get('latestVersion', {}).get('metadataBlocks', {}).get('citation', {}).get('fields', [])
    description_field = next((f for f in fields if f.get('typeName') == 'dsDescription'), None)
    if description_field:
        values = description_field.get('value', [])
        if values:
            return values[0].get('dsDescriptionValue', {}).get('value', "No description found")
    return "No description found"

def get_title(metadata):
    fields = metadata.get('data', {}).get('latestVersion', {}).get('metadataBlocks', {}).get('citation', {}).get('fields', [])
    title_field = next((f for f in fields if f.get('typeName') == 'title'), None)
    if title_field:
        return title_field.get('value', "No title found")
    return "No title found"

def get_version_state(metadata):
    return metadata.get('data', {}).get('latestVersion', {}).get('versionState', "No version found")

def get_persistent_id(metadata):
    return metadata.get('data', {}).get('identifier', "No identifier found")




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




async def render_dashboard(metadata, validation_report, callback):

    test_results = json.loads(validation_report)

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
        check_id = test['check_id'].removesuffix('.xml')

        if check_id in REQUIRED_CHECKS_NAMES:
            required_tests.append({'check_id': HUMAN_READABLE_NAMES.get(check_id, check_id),
                                   'status': test['status'],
                                   'description': CHECK_DESCRIPTIONS.get(check_id, "No description available."),
                                   'output': test.get('output')
                                   })

            if test['status'] == 'SUCCESS':
                passed_required += 1

        if check_id in OPTIONAL_CHECKS_NAMES:
            optional_tests.append({'check_id': HUMAN_READABLE_NAMES.get(check_id, check_id),
                                   'status': test['status'],
                                   'description': CHECK_DESCRIPTIONS.get(check_id, "No description available."),
                                   'output': test.get('output')
                                   })
            if test['status'] == 'SUCCESS':
                passed_optional += 1

        if check_id in INFORMATION_CHECKS_NAMES:
            information_tests.append({'check_id': HUMAN_READABLE_NAMES.get(check_id, check_id),
                                   'status': test['status'],
                                   'description': CHECK_DESCRIPTIONS.get(check_id, "No description available."),
                                   'output': test.get('output')
                                   })
            if test['status'] == 'SUCCESS':
                passed_information += 1

        if test['status'] == 'SUCCESS':
            passed_checks += 1



    description = get_description(metadata)
    title = get_title(metadata)
    version_state = get_version_state(metadata)
    persistent_id = get_persistent_id(metadata)



    return main_dashboard.render(dataset_id=persistent_id,
                           status="Success",
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
                           total_information = len(information_tests),
                           callback=callback
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
                        PRIMARY KEY(dataset_id))
                    """)

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checks(
                        dataset_id TEXT,
                        check_name TEXT NOT NULL,
                        check_description TEXT NOT NULL,
                        check_result_status TEXT NOT NULL,
                        check_result_description TEXT NOT NULL,
                        visibility INTEGER NOT NULL DEFAULT 0 CHECK (visibility IN (0,1)),
                        PRIMARY KEY(dataset_id, check_name),
                        FOREIGN KEY (dataset_id) REFERENCES datasets)
                    """)

    return conn



#takes in metadata and metadata report, caches it into the sqlite database
def cache_report(conn, dataset_id, metadata, report):
    #initialize database if not already
    cursor = conn.cursor()

    #check if we already have a report cached in the database

    cursor.execute("""
                    INSERT INTO datasets (dataset_id, metadata)
                    VALUES (?, ?)
                    ON CONFLICT (dataset_id)
                    DO UPDATE SET metadata=? 
                   """,
                   (dataset_id, json.dumps(metadata), json.dumps(metadata)))

    test_results = report["results"] 

    for test in test_results:
        check_id = test['check_id'].removesuffix('.xml')
        cursor.execute("""
                       INSERT INTO checks (dataset_id, check_name, check_description, check_result_status, check_result_description, visibility)
                       VALUES (?, ?, ?, ?, ?, 1)
                       ON CONFLICT (dataset_id, check_name)
                       DO UPDATE SET check_result_status = ?,
                                     check_result_description = ?
                       """,
                       (dataset_id, check_id, CHECK_DESCRIPTIONS.get(check_id, "No description available"), test['status'], test['output'], test['status'], test['output']))



    conn.commit()
    print(f"Succesfully cached database report")


#Takes in a dataset id
#If there exists a report, returns a tuple of (metadata, report)
#Otherwise returns None
def fetch_cached_report(conn, dataset_id):

    cursor = conn.cursor()

    cursor.execute("""
                    SELECT metadata
                    FROM datasets
                    WHERE dataset_id = ?
                    """,
                   (dataset_id,)
                   )

    row = cursor.fetchone()

    if row is None:
        return None

    metadata = json.loads(row[0])

    cursor.execute("""
                   SELECT *
                   FROM checks
                   WHERE dataset_id = ?
                   """,
                   (dataset_id, )
                   )

    rows = cursor.fetchall()

    check_list = []

    for row in rows:
        check_dict = {
                'check_id': row[1],
                'description':row[2],
                'status':row[3],
                'output':row[4]
                }
        check_list.append(check_dict)     


    return metadata, json.dumps(check_list)




async def toggle_checks(conn, dataset_id, check_list):
    cursor = conn.cursor()
    for check in check_list:
        cursor.execute("""
                    INSERT INTO checks (dataset_id, check, validation)
                    VALUES (?, ?, ?)
                    ON CONFLICT (dataset_id)
                    DO UPDATE SET metadata=?, report=?
                   """,
                   (dataset_id, json.dumps(metadata), json.dumps(report), json.dumps(metadata), json.dumps(report)))









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
    return await render_dashboard(metadata, validation_report, callback)




@app.post("/api/load-new-report")
async def load_new_report(refreshBody: RefreshBody):
    metadata = await get_metadata(refreshBody.callback)
    validation_report = await run_metadata_report(metadata)

    conn = connect_to_database()

    cache_report(conn, refreshBody.dataset_pid, metadata, validation_report)

    #return await render_dashboard(metadata, validation_report)

    return {"message":"succesfully ran and cached new report"}

@app.post("/api/toggle-check-visibility")
async def toggle_check_visibility(checks: ChecksToToggle):
    conn = connect_to_database()



