from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from validator import fetch_metadata_report 
from jinja2 import Environment, PackageLoader, select_autoescape
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

env = Environment(
        loader=PackageLoader("main"),
        autoescape=select_autoescape()
    )

template = env.get_template("mytemplate.html")

app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/")
async def root():
    #return template.render(name_variable="josh")
    return {"Status":"Succesfully connected"}

@app.get("/metadata-report/{dataset_pid:path}", response_class=HTMLResponse)
async def get_metadata_report(dataset_pid:str):
    validation_report = fetch_metadata_report(dataset_pid)

    #return validation_report
    #test_results = validation_report["results"]
    status = validation_report["run_status"]
    test_results = validation_report["results"]
    #return fetch_metadata_report(dataset_pid)
    #return validation_report
    return template.render(dataset_id=dataset_pid,
                           status=status,
                           test_results = test_results
                           )
    


