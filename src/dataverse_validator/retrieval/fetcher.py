import requests
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import sqlite3
from datetime import datetime, timezone




DB_NAME = "reports.db"


#initializes sqlite databases
def initialize_database(database_name):

    current_dir = Path(__file__).resolve().parent

    db_path  = current_dir/ ".." / ".." / ".." / "data" / database_name

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS datasets(
                        id TEXT,
                        report TEXT NOT NULL,
                        PRIMARY KEY(id))
                    """)


    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS latest_time(
                    last_check TEXT,
                    PRIMARY KEY(last_check))
                    """)

    print(f"{database_name} succesfully initialized")

    conn.commit()
    return conn



#takes in last call time(which was stored in the sqlite db) and the updatedAt time returned by the API call
#returns true if the updatedAt time is greater than the previous time, signifying an update
def has_update(last_call_time, api_call_time):

    last_dt = datetime.strptime(last_call_time, "%Y-%m-%d %H:%M:%S")
    api_dt = datetime.strptime(api_call_time, "%Y-%m-%dT%H:%M:%SZ")

    return api_dt > last_dt

#return datasets that have had a draft updated since our last check at last_call_time
#root_dataverse refers to the overall databerse being looked into (is recursive)
def get_updated_datasets(root_dataverse, last_call_time, token, url):

    start = 0
    per_page = 1000
    all_datasets = []

    params = {
            "q": "*",
            "type": "dataset",
            "subtree": root_dataverse,
            "per_page": per_page,
            "fq":"publicationStatus:Draft",
            }


    while True:
        params["start"] = start  # update start each iteration
        res = requests.get(f"{url}/api/search",
                           params=params,
                           headers={"X-Dataverse-key": token})

        data = res.json()["data"]
        for dataset in data["items"]:
            
            if last_call_time is not None:
                if has_update(last_call_time, dataset["updatedAt"]):
                    all_datasets.append(dataset)
            else:
                all_datasets.append(dataset)

        start += per_page
        if start >= data["total_count"]:
            break

    return all_datasets



#returns the time of the last check that is stored in the db
def get_latest_time(conn):
    cursor = conn.cursor()



    cursor.execute("""
                    SELECT LT.last_check
                    FROM latest_time LT
                    """
                   )


    return cursor.fetchone()


#used if there is nothing in the db yet
def initialize_latest_time(conn):
    cursor = conn.cursor()

    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
                    INSERT INTO latest_time(last_check)
                    VALUES (?)
                    """,
                   (current_time,)
                   )

    conn.commit()
    print(f"Succesfully initialized latest_time db to {current_time}")

#used if there is a time in the db already
def update_latest_time(conn):

    cursor = conn.cursor()

    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
                    UPDATE latest_time
                    SET last_check = ?
                    """, (current_time,)
                   )

    conn.commit()
    print(f"Succesfully updated latest_time db to {current_time}")

#takes in name of root dataverse, url of dataverse, and api_token
#returns IDs of new datasets
def fetch(root_name, dataverse_url, api_token):

    conn = initialize_database(DB_NAME)

    last_call_time = get_latest_time(conn)



    try:

        if last_call_time is None:
            datasets = get_updated_datasets(root_name, None, api_token, dataverse_url)

        else:
            datasets = get_updated_datasets(root_name, last_call_time[0], api_token, dataverse_url)





        identifiers = []

        for dataset in datasets:
            identifiers.append(dataset['global_id'])


        if last_call_time is None:
            initialize_latest_time(conn)

        else:
            update_latest_time(conn)

        return identifiers


    except Exception as E:
        print("Error fetching newly modified datasets")

    


    






