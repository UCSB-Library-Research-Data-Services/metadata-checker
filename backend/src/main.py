from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse 
from fastapi.staticfiles import StaticFiles

from pathlib import Path
from pydantic import BaseModel

from utils import helpers, db, templates

from validator import run_metadata_report
class RefreshBody(BaseModel):
    dataset_pid: str
    callback: str

class ToggleVisibility(BaseModel):
    dataset_id: str
    check_id: str



BASE_DIR = Path(__file__).resolve().parent


app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")



@app.get("/")
async def root():
    return {"Status":"Succesfully connected"}

@app.get("/metadata-report", response_class=HTMLResponse)
async def get_metadata_report( callback:str, locale: str):

    conn = db.connect_to_database()

    callback_response = await helpers.get_json(callback)

    if callback_response:
        dataset_pid = callback_response.get('data', {}).get('queryParameters', {}).get('datasetPid')

    else:
        dataset_pid = None


    cached_report_info = db.fetch_cached_report(conn, dataset_pid)
    if cached_report_info is None:
        return await templates.render_empty_dashboard(dataset_pid, callback)

    metadata, validation_report = cached_report_info
    return await templates.render_dashboard(dataset_pid, metadata, validation_report, callback)




@app.post("/api/load-new-report")
async def load_new_report(refreshBody: RefreshBody):
    metadata = await helpers.get_metadata(refreshBody.callback)
    validation_report = await run_metadata_report(metadata)

    conn = db.connect_to_database()

    db.cache_report(conn, refreshBody.dataset_pid, metadata, validation_report)

    return {"message":"succesfully ran and cached new report"}

@app.post("/api/toggle-check-visibility")
async def toggle_check_visibility_route(body: ToggleVisibility):
    conn = db.connect_to_database()
    new_visibility = db.toggle_check_visibility(conn, body.dataset_id, body.check_id)
    return {"visibility": new_visibility}



