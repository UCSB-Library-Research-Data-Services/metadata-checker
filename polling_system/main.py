import requests
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import sqlite3




def initialize_metadata_database():
    conn = sqlite3.connect("metadata_reports.db")
    cursor = conn.cursor()

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS datasets(
                        id TEXT,
                        report TEXT NOT NULL,
                        PRIMARY KEY(id))
                    """)
    print("Metadata db succesfully initialized")
    return conn

def initialize_time_database():
    conn = sqlite3.connect("time.db")
    cursor = conn.cursor()

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS latest_time(
                    last_check TEXT,
                    PRIMARY KEY(last_check))
                    """)

    print("Time db succesfully initialized")
    return conn


def get_updated_datasets(root_dataverse, last_call_time):

    start = 0
    per_page = 1000

    params = {"q":"*",
              "type":"dataset",
              "subtree": root_dataverse,
              #"fq":f"dateSort:[{last_call_time} TO NOW]",
              "per_page": per_page,
              "start":start
           }

    if last_call_time is not None:
        params["fq"] = f"dateSort:[{last_call_time} TO NOW]"



    while True:
        res = requests.get(f"{url}/api/search",
                            params,
                            headers={"X-Dataverse-key": token}
                        )
        start += per_page
        if (start >= res.json()["data"]["total_count"]):
            break

    return res.json()

def get_latest_time(conn):
    cursor = conn.cursor()

    cursor.execute("""
                    SELECT LT.last_check
                    FROM latest_time LT
                    """
                   )

    return cursor.fetchone()


#used if there is nothign in the db yet
def initialize_latest_time(conn):
    cursor = conn.cursor()

#used if there is a time in the db already
def update_latest_time(conn):


if __name__ == '__main__':
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    dotenv_path = parent_dir/'.env'

    load_dotenv(dotenv_path=dotenv_path)

    url = os.getenv("SERVER_URL")
    token = os.getenv("API_TOKEN")
    metadata_conn = initialize_metadata_database()
    time_conn = initialize_time_database()

    last_call_time = get_latest_time(time_conn)
    last_call_time = None


    res = get_updated_datasets("ucsb", last_call_time)
    datasets = res["data"]["items"]

    identifiers = []
    for dataset in datasets:
        identifiers.append(dataset['global_id'])

    print(identifiers)





