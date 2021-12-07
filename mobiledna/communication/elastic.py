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

    time_range = ('2017-01-01T00:00:00.000', '2022-01-01T00:00:00.000')

    # ids = ids_from_server(index='appevents', time_range=time_range)
    # ids = ids_from_file(hlp.DATA_DIR, file_name='test_ids')

    ids = [#"10f815fa-16d4-4efb-a3e5-05b2f197688e",
            #"acdcd702-dcae-45bc-b56f-1f50e4610c2a",
            #"add9ef42-3e0b-4323-bf02-1cedb6ca35c4",
            #"8f9c8eaf-b036-439c-a163-03976bb066d4",
            #"b40238af-1b3a-47bb-b727-12976328b057",
            #"85e750fd-e386-4409-81a6-806fad00af3e",
            #"9b67c710-f5ee-4a4b-ba80-eaf905a1a4fc",
            #"6b953720-4f7a-45f9-aa03-f3199474236c",
            #"3e8c9636-a034-40b7-a979-67025bdd6871",
            #"e0c43c9f-764f-44e9-86af-c80417253ba3",
            #"cdfe7842-bc33-4ecc-9ded-a72bcc2b9f98",
            #"e60fde09-d3fa-441f-a30d-8539354ad6e8",
            #"b7ddaf74-adde-4bdf-9e07-f0d1a06176e7",
            #"20939309-9155-48fa-baa1-51f4d34501ec",
            #"e72a4dc3-a63b-4ee5-b876-70b6eb7cad8e",
            #"5b442d58-78d8-4f3e-9d86-6782dd9945ca",
            #"5fa9da0d-bfcb-48da-8bb3-e245e995e3e6",
            #"cff690d2-a975-4e73-ad07-f5b30f15d0d2",
            #"675d016f-9483-4b1c-b6e0-af4300c4d337",
            #"8273a322-8570-4b3a-89d7-20568c957a1b",
            #"0cb95016-7946-487c-960b-185aa8d9f2a7",
            #"517f011a-f624-461b-94fd-ee6d18a976b3",
            #"cc2aa673-069f-4663-b57a-105d0b3b08bd",
            #"21317632-7f0f-44e7-8120-1ac81c6b093a",
            #"acbf916d-fafc-4f4d-8a2e-eeb3c35d4040",
            #"b50fa764-1a1d-4760-bd6f-6efbba316adb",
            #"2fa4333d-dc1c-4f68-a745-c1cbdf90ed95",
            #"67e8a57c-71f3-4f71-9823-f07a5ed93724",
            #"e24f86ce-5cfe-487a-8f23-929fb7674a4a",
            #"f8e94764-28ef-4af2-9438-54d0ea1205cd",
            #"ffc82bb8-9e10-4bb8-8623-2090be2b9119",
            #"075e5e2b-dd96-4097-8fc3-c3b82f610277",
            #"f7e9ca84-1717-4474-ad37-405eb9ff58a6",
            #"7df858a5-80ee-4ec2-a515-ee369afd9567",
            #"da0b6603-f23d-4804-9722-f08f2dfa160d",
            #"e6f45dc3-afa6-45df-88ee-086ce0cf6a9d",
            #"efcd4689-a4f1-4bcc-810a-57a7c3141f14",
            #"b22ba608-07ba-4f34-a842-8beca10d52ba",
            #"177b0245-8ff4-4a34-b15b-1ddf909e0c9e",
            #"7d4a3521-1ca6-4513-a187-3ff34c46fc13",
            #"846aca1b-242e-4d4f-853b-0d380eeb1e30",
            #"1679e756-74ad-4304-86c8-d9d50fe74fea",
            #"67566970-81f7-4f69-8765-2e1fbe242e62",
            #"92000963-f3aa-4641-b83d-e94ead1e2d35",
            #"fcc76c2b-6fa4-470b-9cb0-b3e37fc60dc7",
            #"140f98ce-2ffe-4aca-accb-76f1cf2f08a9",
            #"5950b2d8-b51a-4c84-86f6-40ee59ddf8c7",
            #"d4c32e44-1428-4745-880b-e820583701e8",
            #"b5aaf5c4-fd3d-4781-9eaf-92e7dee4a234",
            #"d2af4962-7119-41a4-b884-1fb70a48d445",
            #"90b1971d-c70f-495a-bdb0-cc3c5b67bbe1",
            #"d9713ce3-70ee-4dbc-852b-2442998522f7",
            #"4785ed30-240b-4211-b3a9-4fa2c8284819",
            #"f6742014-7eee-4cce-9787-5e4d1ce0a56f",
            #"cba0b16c-995b-4d52-af4d-d4ddeba98c8f",
            #"d43b6efa-9307-498d-bd12-f0040f6a70cb",
            #"1e535f39-f84a-458f-9321-6f078fd706cf",
            "c48454d2-7773-4eca-903e-d89d159c",
            #"52f15a6c-c3dc-4580-8b88-351f6a62d454",
            #"143d4353-584f-4f15-afba-7d59284b5d6e",
            ]

    # Test connectivity export
    data = split_pipeline(ids=ids,
                          dir=os.path.join(hlp.DATA_DIR, 'mdecline', 'mdecline_appevents'),
                          subfolder=False,
                          indices=(['appevents']),
                          time_range=time_range,
                          parquet=True,
                          csv_file=False)


    '''data = pipeline(ids=ids, subfolder=False,
                    name="mdecline",
                          dir=os.path.join(hlp.DATA_DIR, 'mdecline_notifications'),
                          time_range=time_range,
                          indices=(['notifications']),
                          parquet=True,
                          csv_file=False)'''

    #print(data)
