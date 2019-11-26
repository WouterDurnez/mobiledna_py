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

import csv
import os
import random
import sys
from pprint import PrettyPrinter
import base64
import pandas as pd
from elasticsearch import Elasticsearch

import mobiledna.basics.help as hlp
from mobiledna.basics.help import log
import mobiledna.communication.config as cfg

# Globals
pp = PrettyPrinter(indent=4)
indices = hlp.indices
fields = hlp.index_fields
time_var = {
    'appevents': 'startTime',
    'notifications': 'time',
    'sessions': 'timestamp',
    'logs': 'date'
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

    global es

    # Check argument
    if index not in indices:
        raise Exception("ERROR: Counts of active IDs must be based on appevents, sessions, notifications, or logs!")

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
    log("Found {n} active IDs in {index}.\n".format(n=len(ids), index=index), lvl=1)

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

    # Go over most important indices (fuck logs, they're useless).
    for type in {"sessions", "notifications", "appevents"}:

        # Collect counts per id, per index
        ids[type] = ids_from_server(index=type, time_range=time_range)

        # Convert to set so we can figure out intersection
        id_sets[type] = set(ids[type])

    # Calculate intersection of ids
    ids_inter = id_sets["sessions"] & id_sets["notifications"] & id_sets["appevents"]

    log("{n} IDs were found in all indices.\n".format(n=len(ids_inter)), lvl=1)

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

    random_selection = {k: ids[k] for k in random.sample(population=ids.keys(), k=n)}

    return random_selection


###########################################
# Functions to get data, based on id list #
###########################################

def fetch(doc_type: str, ids: list, time_range=('2017-01-01T00:00:00.000', '2020-01-01T00:00:00.000')) -> dict:
    """Fetch data from server"""

    # Are we looking for the right indices?
    if doc_type not in indices:
        raise Exception("Can't fetch data for anything other than appevents,"
                        " notifications or sessions (or logs, but whatever).")

    # If there's more than one ID, recursively call this function
    if len(ids) > 1:

        # Save all results in dict, with ID as key
        dump_dict = {}

        # Go over IDs and try to fetch data
        for index, id in enumerate(ids):

            print("ID {index}: \t{id}".format(index=index + 1, id=id))
            try:
                dump_dict[id] = fetch(doc_type=doc_type, ids=[id], time_range=time_range)[id]
            except:
                print("Fetch failed for {id}".format(id=id))

        return dump_dict

    # If there's one ID, fetch data
    else:

        # Establish connection
        es = connect()

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
                    {time_var[doc_type]:
                         {'format': "yyyy-MM-dd'T'HH:mm:ss.SSS",
                          'gte': start,
                          'lte': stop}
                     }
            }
            body['query']['constant_score']['filter']['bool']['must'].append(range_restriction)

        except:
            print("Failed to restrict range. Getting all data.")

        # Count entries
        count_tot = es.count(index="mobiledna", doc_type=doc_type)
        count_ids = es.count(index="mobiledna", doc_type=doc_type, body=body)

        print("There are {count} entries of the type <{doc_type}>.".format(count=count_tot["count"], doc_type=doc_type))
        print("Selecting {ids} leaves {count} entries.".format(ids=ids, count=count_ids["count"]))

        # Search using scroller (avoid overload)
        res = es.search(index="mobiledna",
                        body=body,
                        request_timeout=120,
                        size=1000,  # Get first 1000 results
                        scroll='30s',  # Get scroll id to get next results
                        doc_type=doc_type)

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
            sys.stdout.write("Entries remaining: {rmn}\r".format(rmn=remaining))
            sys.stdout.flush()

        es.clear_scroll(body={'scroll_id': [scroll_id]})  # Cleanup (otherwise Scroll id remains in ES memory)

        return {ids[0]: dump}


#################################################
# Functions to export data to csv and/or pickle #
#################################################

def export_elastic(dir: str, name: str, index: str, data: dict, pickle=True, csv_file=False):
    """
    Export data to file type (standard CSV file, pickle possible).

    :param dir: location to export data to
    :param name: filename
    :param index: type of data
    :param data: ElasticSearch dump
    :param pickle: would you like that pickled, Ma'am? (bool)
    :param csv_file: export as CSV file (bool, default)
    :return: /
    """

    # Did we get data?
    if data is None:
        raise Exception("ERROR: Received empty data. Failed to export.")

    # Gather data to write to CSV
    to_export = []
    for d in data.values():
        for dd in d:
            to_export.append(dd['_source'])

    # Export file to chosen format
    df = hlp.format_data(pd.DataFrame(to_export), index)

    # Set file name (and have it mention its type for clarity)
    new_name = name + "_" + index

    # Save the data frame
    hlp.save(df=df, dir=dir, name=new_name, csv_file=csv_file, pickle=pickle)


##################################################
# Pipeline functions (general and split up by id #
##################################################

def pipeline(dir: str, name: str, ids: list,
             indices=("appevents", "sessions", "notifications"),
             time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
             pickle=True, csv_file=False):
    """Get all indices sequentially."""

    # All data
    all_df = {}

    # Go over interesting indices
    for index in indices:
        # Get data from server
        print("\nGetting " + index + "...\n")
        data = fetch(doc_type=index, ids=ids, time_range=time_range)

        # Export data
        print("\n\nExporting " + index + "...")
        export_elastic(dir=dir, name=name, index=index, data=data, csv_file=csv_file, pickle=pickle)

        all_df[index] = data

    print("\nDone!\n")

    return all_df


def split_pipeline(dir: str, name: str, ids: list,
                   indices=('appevents', 'notifications', 'sessions', 'logs'),
                   time_range=('2019-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
                   pickle=True, csv_file=False):
    """Same pipeline, but split up for ids."""

    # Go over id list
    for id in ids:
        print("###########################################")
        print("# ID {} #".format(id))
        print("###########################################")

        pipeline(dir=dir,
                 name=id,
                 ids=[id],
                 indices=indices,
                 time_range=time_range,
                 pickle=pickle,
                 csv_file=csv_file)

    print("\nAll done!\n")


########
# MAIN #
########

if __name__ in ['__main__', 'builtins']:
    # Sup?
    hlp.hi()

    ids = ["d1002904-3a30-4515-816e-ef5b6b8ec84a",
           "273f3a6e-d724-4ed3-80e7-d9ec73b3ad24"]

    # Set time range
    """data = pipeline(
        dir="../../../data/",
        name="191120_lfael",
        ids=ids,
        time_range=('2019-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
        pickle=False,
        csv_file=True,
        doc_types={"appevents"}
    )

    df = data['appevents']"""
    # ids = ids_from_server(index='appevents', time_range=('2019-01-01T00:00:00.000', '2020-01-01T00:00:00.000'))
    split_pipeline(dir="../../data/",
                   ids=ids,
                   name='test', indices=('appevents',),
                   time_range=('2019-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
                   pickle=False,
                   csv_file=True)
