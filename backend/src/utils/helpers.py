import base64
import httpx
from fastapi import HTTPException
import json
from constants import CHECK_DESCRIPTIONS, HUMAN_READABLE_NAMES



#Parses description from metadata
def get_description(metadata):
    fields = metadata.get('data', {}).get('latestVersion', {}).get('metadataBlocks', {}).get('citation', {}).get('fields', [])
    description_field = next((f for f in fields if f.get('typeName') == 'dsDescription'), None)
    if description_field:
        values = description_field.get('value', [])
        if values:
            return values[0].get('dsDescriptionValue', {}).get('value', "No description found")
    return "No description found"

#Parses title from metadata
def get_title(metadata):
    fields = metadata.get('data', {}).get('latestVersion', {}).get('metadataBlocks', {}).get('citation', {}).get('fields', [])
    title_field = next((f for f in fields if f.get('typeName') == 'title'), None)
    if title_field:
        return title_field.get('value', "No title found")
    return "No title found"

#Parses version state from metadata
def get_version_state(metadata):
    return metadata.get('data', {}).get('latestVersion', {}).get('versionState', "No version found")



#Takes in a callback URL from Dataverse and uses it to get the metadata
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




#Takes in callback URL from Dataverse, hits the endpoint, and then returns the json response
async def get_json(callback):
    decoded_url = base64.b64decode(callback).decode("utf-8")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(decoded_url)
            res.raise_for_status()
            return res.json()
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Dataverse callback failed")








