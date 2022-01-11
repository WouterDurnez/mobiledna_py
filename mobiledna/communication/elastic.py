# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

ELASTICSEARCH FUNCTIONS

-- Coded by Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import base64
import csv
import os
import random as rnd
import sys
from pprint import PrettyPrinter

import pandas as pd
from elasticsearch import Elasticsearch

import mobiledna.communication.config as cfg
import mobiledna.core.help as hlp
from mobiledna.core.help import log

# Globals
pp = PrettyPrinter(indent=4)
indices = hlp.INDICES
fields = hlp.INDEX_FIELDS
time_var = {
    'appevents': 'startTime',
    'notifications': 'time',
    'sessions': 'timestamp',
    'logs': 'date',
    'connectivity': 'timestamp'
}
es = None


#######################################
# Connect to ElasticSearch repository #
#######################################

def connect(server=cfg.server, port=cfg.port) -> Elasticsearch:
    """
    Establish connection with data.

    :param server: server address
    :param port: port to go through
    :return: Elasticsearch object
    """

    server = base64.b64decode(server).decode("utf-8")
    port = int(base64.b64decode(port).decode("utf-8"))

    es = Elasticsearch(
        hosts=[{'host': server, 'port': port}],
        timeout=100,
        max_retries=10,
        retry_on_timeout=True
    )

    log("Successfully connected to server.")

    return es


##############################################
# Functions to load IDs (from server or file #
##############################################

def ids_from_file(dir: str, file_name='ids', file_type='csv') -> list:
    """
    Read IDs from file. Use this if you want to get data from specific
    users, and you have their listed their IDs in a file.

    :param dir: directory to find file in
    :param file_name: (sic)
    :param file_type: file extension
    :return: list of IDs
    """

    # Create path
    path = os.path.join(dir, '{}.{}'.format(file_name, file_type))

    # Initialize id list
    id_list = []

    # Open file, read lines, store in list
    with open(path) as file:
        reader = csv.reader(file)
        for row in reader:
            id_list.append(row[0])

    return id_list


def ids_from_server(index="appevents",
                    time_range=('2018-01-01T00:00:00.000', '2030-01-01T00:00:00.000')) -> dict:
    """
    Fetch IDs from server. Returns dict of user IDs and count.
    Can be based on appevents, sessions, notifications, or logs.

    :param index: type of data
    :param time_range: time period in which to search
    :return: dict of user IDs and counts of entries
    """

    # Check argument
    if index not in indices:
        raise Exception("ERROR: Counts of active IDs must be based on appevents, sessions, notifications, or logs!")

    global es

    # Connect to es server
    if not es:
        es = connect()

    # Log
    log("Getting IDs that have logged {doc_type} between {start} and {stop}.".format(
        doc_type=index, start=time_range[0], stop=time_range[1]))

    # Build ID query
    body = {
        "size": 0,
        "aggs": {
            "unique_id": {
                "terms": {
                    "field": "id.keyword",
                    "size": 1000000
                }
            }
        }
    }

    # Change query if time is factor
    try:
        start = time_range[0]
        stop = time_range[1]
        range_restriction = {
            'range':
                {time_var[index]:
                     {'format': "yyyy-MM-dd'T'HH:mm:ss.SSS",
                      'gte': start,
                      'lte': stop}
                 }
        }
        body['query'] = {
            'bool': {
                'filter':
                    range_restriction

            }
        }

    except:
        raise Warning("WARNING: Failed to restrict range. Getting all data.")

    # Search using scroller (avoid overload)
    res = es.search(index='mobiledna',
                    body=body,
                    request_timeout=300,
                    scroll='30s',  # Get scroll id to get next results
                    doc_type=index)

    # Initialize dict to store IDs in.
    ids = {}

    # Go over buckets and get count
    for bucket in res['aggregations']['unique_id']['buckets']:
        ids[bucket['key']] = bucket['doc_count']

    # Log
    log("Found {n} active IDs in {index}.\n".
        format(n=len(ids), index=index), lvl=1)

    return ids


################################################
# Functions to filter IDs (from server or file #
################################################

def common_ids(index="appevents",
               time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000')) -> dict:
    """
    This function attempts to find those IDs which have the most complete data, since there have been
    problems in the past where not all data get sent to the server (e.g., no notifications were registered).
    The function returns a list of IDs that occur in each index (apart from the logs, which may occur only
    once at the start of logging, and fall out of the time range afterwards).

    The function returns a dictionary, where keys are the detected IDs, and values correspond with
    the number of entries in an index of our choosing.

    :param index: index in which to count entries for IDs that have data in each index
    :param time_range: time period in which to search
    :return: dictionary with IDs for keys, and index entries for values
    """

    ids = {}
    id_sets = {}

    # Go over most important INDICES (fuck logs, they're useless).
    for type in {"sessions", "notifications", "appevents"}:
        # Collect counts per id, per index
        ids[type] = ids_from_server(index=type, time_range=time_range)

        # Convert to set so we can figure out intersection
        id_sets[type] = set(ids[type])

    # Calculate intersection of ids
    ids_inter = id_sets["sessions"] & id_sets["notifications"] & id_sets["appevents"]

    log("{n} IDs were found in all INDICES.\n".format(n=len(ids_inter)), lvl=1)

    return {id: ids[index][id] for id in ids_inter}


def richest_ids(ids: dict, top=100) -> dict:
    """
    Given a dictionary with IDs and number of entries,
    return top X IDs with largest numbers.

    :param ids: dictionary with IDs and entry counts
    :param top: how many do you want (descending order)? Enter 0 for full sorted list
    :return: ordered subset of IDs
    """

    if top == 0:
        top = len(ids)

    rich_selection = dict(sorted(ids.items(), key=lambda t: t[1], reverse=True)[:top])

    return rich_selection


def random_ids(ids: dict, n=100) -> dict:
    """Return random sample of ids."""

    random_selection = {k: ids[k] for k in rnd.sample(population=ids.keys(), k=n)}

    return random_selection


###########################################
# Functions to get data, based on id list #
###########################################

def fetch(index: str, ids: list, time_range=('2017-01-01T00:00:00.000', '2020-01-01T00:00:00.000')) -> dict:
    """
    Fetch data from server, for given ids, within certain timeframe.

    :param index: type of data we will gather
    :param ids: only gather data for these IDs
    :param time_range: only look in this time range
    :return: dict containing data (ES JSON format)
    """
    global es

    # Establish connection
    if not es:
        es = connect()

    # Are we looking for the right INDICES?
    if index not in indices:
        raise Exception("Can't fetch data for anything other than appevents,"
                        " notifications, sessions or connectivity (or logs, but whatever).")

    count_tot = es.count(index="mobiledna", doc_type=index)
    log("There are {count} entries of the type <{index}>.".
        format(count=count_tot["count"], index=index), lvl=3)

    # Make sure IDs is the list (kind of unpythonic)
    if not isinstance(ids, list):
        log("WARNING: ids argument was not a list (single ID?). Converting to list.", lvl=1)
        ids = [ids]

    # If there's more than one ID, recursively call this function
    if len(ids) > 1:

        # Save all results in dict, with ID as key
        dump_dict = {}

        # Go over IDs and try to fetch data
        for idx, id in enumerate(ids):

            log("Getting data: ID {id_index}/{total_ids}: \t{id}".format(
                id_index=idx + 1,
                total_ids=len(ids),
                id=id))

            try:
                dump_dict[id] = fetch(index=index, ids=[id], time_range=time_range)[id]
            except Exception as e:
                log("Fetch failed for {id}: {e}".format(id=id, e=e), lvl=1)

        return dump_dict

    # If there's one ID, fetch data
    else:

        # Base query
        body = {
            'query': {
                'constant_score': {
                    'filter': {
                        'bool': {
                            'must': [
                                {
                                    'terms':
                                        {'id.keyword':
                                             ids
                                         }
                                }
                            ]

                        }
                    }
                }
            }
        }

        # Chance query if time is factor
        try:
            start = time_range[0]
            stop = time_range[1]
            range_restriction = {
                'range':
                    {time_var[index]:
                         {'format': "yyyy-MM-dd'T'HH:mm:ss.SSS",
                          'gte': start,
                          'lte': stop}
                     }
            }
            body['query']['constant_score']['filter']['bool']['must'].append(range_restriction)

        except:
            log("WARNING: Failed to restrict range. Getting all data.", lvl=1)

        # Count entries
        count_ids = es.count(index="mobiledna", doc_type=index, body=body)

        log("Selecting {ids} yields {count} entries.".format(ids=ids, count=count_ids["count"]), lvl=2)

        # Search using scroller (avoid overload)
        res = es.search(index="mobiledna",
                        body=body,
                        request_timeout=120,
                        size=1000,  # Get first 1000 results
                        scroll='30s',  # Get scroll id to get next results
                        doc_type=index)

        # Update scroll id
        scroll_id = res['_scroll_id']
        total_size = res['hits']['total']

        # Save all results in list
        dump = res['hits']['hits']

        # Get data
        temp_size = total_size

        ct = 0
        while 0 < temp_size:
            ct += 1
            res = es.scroll(scroll_id=scroll_id,
                            scroll='30s',
                            request_timeout=120)
            dump += res['hits']['hits']
            scroll_id = res['_scroll_id']
            temp_size = len(res['hits']['hits'])  # As long as there are results, keep going ...
            remaining = (total_size - (ct * 1000)) if (total_size - (ct * 1000)) > 0 else temp_size
            sys.stdout.write("Entries remaining: {rmn} \r".format(rmn=remaining))
            sys.stdout.flush()

        es.clear_scroll(body={'scroll_id': [scroll_id]})  # Cleanup (otherwise scroll ID remains in ES memory)

        return {ids[0]: dump}


#################################################
# Functions to export data to csv and/or pickle #
#################################################

def export_elastic(dir: str, name: str, index: str, data: dict, pickle=True, csv_file=False, parquet=False):
    """
    Export data to file type (standard CSV file, pickle possible).

    :param dir: location to export data to
    :param name: filename
    :param index: type of data
    :param data: ElasticSearch dump
    :param pickle: would you like that pickled, Ma'am? (bool)
    :param csv_file: export as CSV file (bool, default)
    :param parquet: export as parquet file (bool)
    :return: /
    """

    # Does the directory exist? If not, make it
    hlp.set_dir(dir)

    # Did we get data?
    if data is None:
        raise Exception("ERROR: Received empty data. Failed to export.")

    # Gather data for data frame export
    to_export = []
    for id, d in data.items():

        # Check if we got data!
        if not d:
            log(f"WARNING: Did not receive data for {id}!", lvl=1)
            continue

        for dd in d:
            to_export.append(dd['_source'])

    # If there's no data...
    if not to_export:

        log(f"WARNING: No data to export!", lvl=1)

    else:
        # ...else, convert to formatted data frame
        df = hlp.format_data(pd.DataFrame(to_export), index)

        # Set file name (and have it mention its type for clarity)
        new_name = name + "_" + index

        # Save the data frame
        hlp.save(df=df, dir=dir, name=new_name, csv_file=csv_file, pickle=pickle, parquet=parquet)


##################################################
# Pipeline functions (general and split up by id #
##################################################

@hlp.time_it
def pipeline(name: str, ids: list, dir: str,
             indices=('appevents', 'sessions', 'notifications', 'logs', 'connectivity'),
             time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
             subfolder=False,
             pickle=False, csv_file=True, parquet=False):
    """
    Get data across multiple INDICES. By default, they are stored in the same folder.

    :param name: name of dataset
    :param ids: IDs in dataset
    :param dir: directory in which to store data
    :param indices: types of data to gather (default: all)
    :param time_range: only look in this time range
    :param pickle: (bool) export as pickle (default = False)
    :param csv_file: (bool) export as CSV file (default = True)
    :return:
    """

    log("Begin pipeline for {number_of_ids} IDs, in time range {time_range}.".format(
        number_of_ids=len(ids),
        time_range=time_range
    ))

    # All data
    all_df = {}

    # Go over interesting INDICES
    for index in indices:
        # Get data from server
        log("Getting started on <" + index + ">...", lvl=1)
        data = fetch(index=index, ids=ids, time_range=time_range)

        # Export data
        log("Exporting <" + index + ">...", lvl=1)

        # If requested, add to different subfolder
        dir_new = os.path.join(dir, index) if subfolder else dir

        # If this directory doesn't exist, make it
        # hlp.set_dir(dir_new)

        # Export to file
        export_elastic(dir=dir_new, name=name, index=index, data=data, csv_file=csv_file, pickle=pickle,
                       parquet=parquet)

        print("")

        all_df[index] = data

    log("DONE!")

    return all_df


@hlp.time_it
def split_pipeline(ids: list, dir: str,
                   indices=('appevents', 'notifications', 'sessions', 'logs', 'connectivity'),
                   time_range=('2019-10-01T00:00:00.000', '2020-02-01T00:00:00.000'),
                   subfolder=False,
                   pickle=False, csv_file=False, parquet=True) -> list:
    """
    Get data across INDICES, but split up per ID. By default, create subfolders.

    :param ids: IDs in dataset
    :param dir: directory in which to store data
    :param indices: types of data to gather (default: all)
    :param time_range:
    :param pickle:
    :param csv_file:
    :return: list of ids that weren't fetched successfully
    """

    # Make sure IDs is the list (kind of unpythonic)
    if not isinstance(ids, list):
        log("WARNING: ids argument was not a list (single ID?). Converting to list.", lvl=1)
        ids = [ids]

    # Gather ids for which fetch failed here
    failed = []

    # Go over id list
    for index, id in enumerate(ids):
        log(f"Getting started on ID {id} ({index + 1}/{len(ids)})", title=True)

        try:
            pipeline(dir=dir,
                     name=str(id),
                     ids=[id],
                     indices=indices,
                     time_range=time_range,
                     subfolder=subfolder,
                     parquet=parquet,
                     pickle=pickle,
                     csv_file=csv_file)
        except Exception as e:
            log(f"Failed to get data for {id}: {e}", lvl=1)
            failed.append(id)

    log("\nALL DONE!\n")
    return failed


########
# MAIN #
########

if __name__ in ['__main__', 'builtins']:
    # Sup?
    hlp.hi()
    hlp.set_param(log_level=3)

    time_range = ('2016-01-01T00:00:00.000', '2022-01-01T00:00:00.000')

    # ids = ids_from_server(index='appevents', time_range=time_range)
    # ids = ids_from_file(hlp.DATA_DIR, file_name='test_ids')

    ids = [
        "c081492d-a752-41df-8971-59bac6d98eae",
        "5ac290ac-6403-4450-b4cc-7bfabe0c8871",
        "098473e7-c27f-4920-b91f-e88fbdf70def",
        "356b5d1d-ed6e-47b0-a136-d1ecfafbf7fc",
        "ab7a17ae-8ea0-46a5-962f-4302f9792011",
        "d7f3d1ba-e2a6-42fe-ae5b-8b373a13c42d",
        "bf5c1b9e-3c9f-4578-b6e9-cb71cc407d82",
        "dcec1764-5744-4a87-b002-e314df9746c0",
        "30576dcc-11af-455e-89f2-376615721606",
        "20e11fae-4954-4477-a55d-d52591173e62",
        "9fb2b17f-c0ad-49ea-b647-b57f3b4fb6bd",
        "adbb1132-3d33-4f8d-81c9-fb96e612fa6c",
        "18ec705e-7a3b-4a75-8646-b301bf375c8a",
        "067815dd-4b81-4d75-a6da-a0670f9157a4",
        "0073ce5e-fe79-4a58-a1bf-20088ef7dcb5",
        "107a4cca-4467-424b-94e4-112104c17d72",
        "836d78d3-00a2-4b10-be0f-f10f60576e6d",
        "645a2501-b148-4c1a-8b21-dae70c9a1a80",
        "eab1e574-9ac3-449d-bc91-4a4114daa304",
        "1c1e79ae-0bbc-4f77-b31d-5e85ae77dab6",
        "3d20db39-8ef5-4402-b382-5504b4674533",
        "dcf31fd5-b1c5-47e8-8f17-d7d939511110",
        "c40f4771-fb9c-4fd2-9eb5-0a90f49c9eef",
        "bb8a94d1-4b51-490a-95a7-9a5a0863c44f",
        "753645cc-0372-4bee-a7ec-314da217a471",
        "cfb007b6-dc21-49e9-aab3-f43ea9a6edc5",
        "1a093193-72bc-4324-a6b6-7dc9dbf19583",
        "8db74455-3431-406c-8f05-013e3c04c9f2",
        "61397f79-e921-4ee2-9641-47ffcc4b15f5",
        "750803b5-9e0d-4a0c-8863-d463e99e7fbf",
        "467d3fd5-e1dd-48de-bd74-e2e2e6812815",
        "1c93c484-066a-4045-b686-6181cee59cbe",
        "003f2cd5-55d7-40a0-b6b5-87f881e7523b",
        "296b97fa-d124-41cf-a62f-19886ffd13da",
        "12306ea7-33a3-4cb6-831a-5c15ed8376cb",
        "d9e3b33d-89c3-4f9d-a6ef-c7ee421bd5e4",
        "8a92181c-7b3b-423a-a708-513341c80b8d",
        "d1ee0a78-97f4-4635-8508-2b9577cf0974",
        "43d1623b-ef99-4cdd-8fc1-d1698e0115a3",
        "7af13afa-d473-4db5-bb44-586c290fac1c",
        "4f469850-bfdb-47b7-b443-c0ea5314fb73",
        "4341d20d-11f8-4bbb-84c9-9d2fb7d96b43",
        "33c45621-6559-4549-bcf3-066c8c75a719",
        "7ac3f36c-dc7a-4935-bcb9-d5b41215fe81",
        "42c3c070-b635-43fb-b7c5-2e89593ec347",
        "605ca41c-0de5-40a2-b791-911f967bb59f",
        "35c1c2db-831c-4a09-b9b7-a21809543acd",
        "3d7a2e93-ca01-42f3-8a32-9eedaf17052a",
        "a638217e-d73c-4f82-90f9-2b8f6645df41",
        "c1e6a1c4-f2e7-4be1-b2c6-9576af039e79",
        "835d81f1-a715-472e-b811-a325565abf6b",
        "ae179889-81a4-43dd-9995-bee353744368",
        "4a4086f2-9ff1-4ae7-8c9d-377815be99e5",
        "e9abdc89-c06c-464f-a013-6fe453e426f2",
        "ae84aeb6-66b2-4942-b1a8-c2a8d87e938e",
        "d723db69-e093-4d47-abc1-02dc9c54851c",
        "0e6fa3ac-2f40-40c6-b4c6-cee66659b5fa",
        "96f37d1a-50ae-4558-999c-2f4f0d16b35d",
        "169b0bf5-8c6d-4f29-80ba-c1afc6958eb7",
        "5748f17e-9205-4ca0-9dea-0b0a6233d373",
        "284c9c24-3026-41d3-af5b-443b1d84c989",
        "0ddc0b59-1cbb-4862-a2bb-d032a8f6f67e",
        "eb95597c-f68a-48ed-bb4b-809abc6de058",
        "eeee9296-2943-4af6-bd4f-4fad67e9c7e9",
        "0f58fb44-e462-466d-84eb-331a267e12e0",
        "901d2a62-4852-4c53-ae2e-56c8326b1b54",
        "6f63f6fc-5c77-4600-9b74-5266399667b6",
        "8061fc9a-934c-42eb-908d-e092e62514d6",
        "9cb90b1b-d071-4723-a628-92cb5028e8d8",
        "a968ea41-73b3-4860-bde6-73a927870d54",
        "44951d96-9817-4baf-bae2-bba6b32d1f31",
        "92624b67-8c9e-40d0-94ad-cc18c14002a4",
        "aae224d9-28c9-47cc-9bfd-22132942f8eb",
        "c58045a6-425a-430d-8784-7ef642fcdbe8",
        "2f5d3a3f-22d8-4152-bc6e-55ffe7e1337e",
        "aafd7c21-1cbc-4ee8-85d2-10801ef5e620",
        "a4c6959c-7704-479a-959d-09209a1d8041",
        "3b8ffd4d-a70c-4cd0-8fc2-c4dd1fd5aede",
        "13bf104d-d1c6-41bc-914b-be0d9cf0681d",
        "83ee8a3b-760c-4d8f-96ae-0f5fdddabe29",
        "c628ef0f-566c-48a5-b27c-9ed09a86eef5",
        "1adca3a9-9c45-473a-803e-1525f9fe9c6a",
        "0499aba4-832c-4487-82c9-aebfaec6eb3b",
        "58ca8c99-f22c-4ba2-b533-65867e35efd7",
        "a06ff148-62c5-47af-9b8c-95902cbf8b23",
        "45a7af30-5e3e-4d9f-bae8-146bba473d1d",
        "47a8d70b-74a4-4961-a404-6cf256bf0b6e",
        "55161a26-ee74-4866-ab54-c9168041603d",
    ]

    # Test connectivity export
    """data = split_pipeline(ids=ids,
                          dir=os.path.join(hlp.DATA_DIR, 'mdna_2021_sample', 'mdecline-appevents'),
                          subfolder=False,
                          indices=(['appevents']),
                          time_range=time_range,
                          parquet=True,
                          csv_file=False)"""


    data = pipeline(ids=ids, subfolder=False,
                    name="socdna",
                          dir=os.path.join(hlp.DATA_DIR, 'socdna'),
                          time_range=time_range,
                          indices=(['appevents']),
                          parquet=True,
                          csv_file=False)

    #print(data)
