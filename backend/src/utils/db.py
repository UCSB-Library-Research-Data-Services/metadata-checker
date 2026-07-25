from pathlib import Path
import sqlite3
import json
from constants import DB_NAME, CHECK_DESCRIPTIONS
from fastapi import HTTPException



#Connect to sqlite3 database and initialize datasets table, returns connection
def connect_to_database():

    current_dir = Path(__file__).resolve().parent

    db_path  = current_dir/ ".." / ".." / "data" / DB_NAME

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
                       (dataset_id, check_id, CHECK_DESCRIPTIONS.get(check_id, "No description available"), test['status'], json.dumps(test['output']), test['status'], json.dumps(test['output'])))



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
                'output':json.loads(row[4]),
                'visibility':row[5]
                }
        check_list.append(check_dict)     


    return metadata, json.dumps(check_list)



def toggle_check_visibility(conn, dataset_id, check_id):
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT visibility FROM checks
                   WHERE dataset_id = ? AND check_name = ?
                   """,
                   (dataset_id, check_id))
    row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No check found")
    new_visibility = 1 - row[0]
    cursor.execute("""
                   UPDATE checks SET visibility = ?
                   WHERE dataset_id = ? AND check_name = ?
                   """,
                   (new_visibility, dataset_id, check_id))
    conn.commit()
    return new_visibility
