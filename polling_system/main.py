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
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS datasets(
                        id TEXT,
                        report TEXT NOT NULL,
                        PRIMARY KEY(id))
                    """)
    print(f"{database_name} succesfully initialized")


    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS latest_time(
                    last_check TEXT,
                    PRIMARY KEY(last_check))
                    """)

    conn.commit()
    return conn


#This function works for things that were created, but not drafts
#def get_updated_datasets(root_dataverse, last_call_time):
    #dt = datetime.strptime(last_call_time, "%Y-%m-%d %H:%M:%S")
    #timestamp = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    #start = 0
    #per_page = 1000
    #all_datasets = []

    #params = {
            #"q": "*",
            #"type": "dataset",
            #"subtree": root_dataverse,
            #"per_page": per_page,
            #}

    #if last_call_time is not None:
        #params["fq"] = f"dateSort:[{timestamp} TO NOW]"
        #print(timestamp)

    #while True:
        #params["start"] = start  # update start each iteration
        #res = requests.get(f"{url}/api/search",
                           #params=params,
                           #headers={"X-Dataverse-key": token})

        #data = res.json()["data"]
        #all_datasets.extend(data["items"])  # accumulate results

        #start += per_page
        #if start >= data["total_count"]:
            #break

    #return all_datasets


#takes in last call time(which was stored in the sqlite db) and the updatedAt time returned by the API call
#returns true if the updatedAt time is greater than the previous time, signifying an update
def has_update(last_call_time, api_call_time):

    last_dt = datetime.strptime(last_call_time, "%Y-%m-%d %H:%M:%S")
    api_dt = datetime.strptime(api_call_time, "%Y-%m-%dT%H:%M:%SZ")

    return api_dt > last_dt

#return datasets that have had a draft updated since our last check at last_call_time
#root_dataverse refers to the overall databerse being looked into (is recursive)
def get_updated_datasets(root_dataverse, last_call_time):

    start = 0
    per_page = 1000
    all_datasets = []

    params = {
            "q": "*",
            "type": "dataset",
            "subtree": root_dataverse,
            "per_page": per_page,
            }


    while True:
        params["start"] = start  # update start each iteration
        res = requests.get(f"{url}/api/search",
                           params=params,
                           headers={"X-Dataverse-key": token})

        data = res.json()["data"]
        for dataset in data["items"]:
            if has_update(last_call_time, dataset["updatedAt"]):
                all_datasets.append(dataset)

        start += per_page
        if start >= data["total_count"]:
            break

    print(all_datasets)
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


if __name__ == '__main__':
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    dotenv_path = parent_dir/'.env'

    load_dotenv(dotenv_path=dotenv_path)

    url = os.getenv("SERVER_URL")
    token = os.getenv("API_TOKEN")
    conn = initialize_database(DB_NAME)

    last_call_time = get_latest_time(conn)


    try:
        datasets = get_updated_datasets("ucsb", last_call_time[0])

        identifiers = []
        for dataset in datasets:
            identifiers.append(dataset['global_id'])

        if last_call_time is None:
            initialize_latest_time(conn)
        else:
            update_latest_time(conn)

        print(identifiers)



    except Exception as E:
        print("Error gettingresponse")
        print(E)

    


    






