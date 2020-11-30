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
                   subfolder=True,
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

    time_range = ('2020-06-01T00:00:00.000', '2020-12-01T00:00:00.000')

    # ids = ids_from_server(index='appevents', time_range=time_range)
    # ids = ids_from_file(hlp.DATA_DIR, file_name='glance_ids')

    '''ids = [
        "0a8ee96a-a76c-4c9d-b808-947b32c745de",
        "a0b8672d-6d4b-4b82-8bae-f14b8f2ce932",
        "d0288296-2e0d-4dac-826f-5cd5f239c240",
        "82af8961-c92b-4e87-bb19-f9d790b7427d",
        "a18ce6f9-a033-4eaf-833e-362a7e1aec3c"
    ]'''

    ids = [
        '00cbc8e4-edd6-4842-90e0-e13b957ffb8b',
        '01f0fe8b-d868-488c-b0a8-cd95421810b2',
        '04dd491f-b138-41a9-9913-44f5b355bd66',
        '055e60e2-75ac-44fc-a4af-4ca8df59a7ab',
        '07f11866-e260-4ce2-8113-815d23ae3013',
        '08f1e0af-58b1-470e-acf5-8ab0a5835baf',
        '0b316519-bee7-4a5c-8524-8a84399a1ed4',
        '0c3c2855-c7eb-43c4-bac4-b9266a7b4d96',
        '10ea9e47-b01b-4292-a74e-d576edd26b17',
        '146151a4-179e-4532-b20b-b6c256114f49',
        '14783b43-e5ca-4ba8-a7cc-6a83a85808c9',
        '17023bad-0519-405c-b2d4-37c56dda776e',
        '17202291-99f0-4de6-8493-a62c2b1f3ac3',
        '1a60dd44-6eda-45ae-b3dc-529f03aef53b',
        '1ce8eabc-5941-4d19-8440-dd9fab49606a',
        '1dcaa002-d6ec-4c14-82ec-fcf18b22bab7',
        '1e20be25-ae79-4e07-b39b-fcadc26b4f78',
        '21266c6a-53a2-4386-bd3d-2f2231b31202',
        '274d7a37-e6d7-4fb8-8d1b-5b6fe270c629',
        '27ff463f-0e5a-48df-9335-bd4281b29c81',
        '2814987a-5f19-45ba-bf37-dd84654c5e94',
        '29673205-ec65-4f9f-ac14-5d880693afaa',
        '2a4722c0-e3f1-4641-b93b-b379a2747b60',
        '2b9ad66c-ce4f-437a-9f1e-dd7f6b7c83de',
        '2cdc9c5a-2bc8-40bc-b5c7-cc0eb5877210',
        '2d5e34cb-b15e-4f09-b1e2-94b153c6bf99',
        '2d9b82da-a862-4cc5-a223-7705195b2da4',
        '30118a8c-dd37-4f88-83d1-4cd94e9de82e',
        '305a75f9-ff11-4390-a03e-bbe3a4241d0c',
        '307103bd-fa72-4da9-a087-2d2ffac31816',
        '30a738b2-b0a5-479c-98b6-1ce8a90ffa93',
        '3110c029-c4fd-4d4e-9f0f-916ea0edb269',
        '31bb7fe3-bc7b-4eef-bb92-c27a3bd038da',
        '33e8c378-0c4c-4ca6-aa21-61971d6f5765',
        '359377a2-20f7-4a54-97d9-4b714ce46e43',
        '35a6873f-e432-4184-9cd6-3973824f3258',
        '3699ab15-ae44-4946-ad03-0715e3db8ced',
        '3a215c83-2e8b-4481-9668-5a0e60a83e36',
        '3a6579d2-78bc-47ca-a961-75bdf5df912c',
        '3a7ba6f4-661a-4b60-8bb8-c6b2c4626f38',
        '3c719547-bca6-446b-98c9-16655b394c43',
        '3c88dce2-65c5-4fcb-bcc4-e1a670bbd0ed',
        '3e76b28a-af96-4117-9190-2882e8e2f82b',
        '3f306614-bfef-43b9-b1e2-e5128b23e481',
        '4082e5c2-e115-4a64-b450-dadc78f49638',
        '42fde60b-9138-46e2-a80d-fe90cb93cbbe',
        '43e19cb0-fcf4-4d60-ae38-2d3e029b0aef',
        '45008c76-3797-467a-8509-8af382bf87b4',
        '4d136929-0e8f-4073-83de-cbf146a7add4',
        '4e80723e-080f-4457-98f5-1eaac0bdfdda',
        '4f52d053-88a7-4f0e-98bf-758b358c9264',
        '51623806-e3fd-4473-9584-263a08a6d7eb',
        '546df05b-160f-407b-bd4c-97d534c64f86',
        '55847faf-a1f5-4895-a2a3-4fb162c5bc96',
        '5876f9ca-89f3-4a36-aa00-51bd33dfa584',
        '58bfd5ad-f232-45ef-a6b5-67e5963ae73b',
        '59676111-9d18-4837-bf16-39d203f95098',
        '5a786371-d05a-4a3a-85f6-7fb980182a89',
        '5bec7824-b2e0-458f-82ed-df48685d099a',
        '5e7df454-e0b0-41cd-88b8-0c549a379ed3',
        '5f0ae215-a9f3-4930-b3af-cf6ccbc41d94',
        '5f49e575-748d-46a6-b9a7-d6ec7c9ca4b5',
        '6245a583-0eb6-47a5-9ed9-fed7607b8e5c',
        '62fceeb5-943d-4f1e-b5ad-7130133d1765',
        '640a3937-b782-4f3e-af05-d299411d78ff',
        '64ba006e-43fd-41f0-9f16-88bf7ef53306',
        '64e92abe-f2c6-420c-8456-f71ec3fe30ca',
        '660dc56f-08af-484f-b335-8ace5844c02f',
        '674c0444-d8cc-4599-9224-22710018c58e',
        '6ae30d64-0610-4a17-a380-0d804d353762',
        '6c5b4753-cedf-462a-872e-10eedccf1f07',
        '6d88532b-e0e8-43d9-9fe5-2c5f0871ba87',
        '6e266579-de0b-465a-84a7-2f49d350c9cb',
        '703a4b8e-185a-480c-84aa-69ae4d99dbf6',
        '70b9ea4a-dfb5-42e1-b122-f2f0a05a6ab3',
        '725fa1aa-f33f-4992-8217-e2a8b9c38724',
        '7417a074-a89a-4a22-bf7a-d29145751bf5',
        '742f8f99-f6cc-454c-90b6-f88e4b65ebc7',
        '75fb0bc6-a7dd-47bc-8741-7d3629ca4d0c',
        '77f94091-4e8c-4a00-b6a7-6d37b8de4c33',
        '78e0ca53-3583-4527-a7e7-b3eacda51a38',
        '7969c573-ac14-49df-a38f-3a60f54f7f3a',
        '7a3425bd-bd92-4bb7-b61e-086cbe5f27d7',
        '8078efbd-374b-42d0-859b-1c8be9782eb8',
        '8320df2a-61e4-40a1-835b-acaadabafa8f',
        '864598d5-582b-4621-b361-6924a5cccb4e',
        '8670c60d-871b-4c5f-a46f-21cb947bd481',
        '86c70069-cd49-457e-b45d-221fdd94d94c',
        '88f1d690-a60d-4e4e-963f-02cd6ad7a09c',
        '8b86acba-c02e-4a54-af97-376cb4fbd765',
        '8bd06a5d-9fe4-4484-a86f-4bebe4306994',
        '8d187d79-663b-493e-8029-8fa89bce2e1c',
        '8fd1285d-1daa-4277-90dc-d1c3edf467fe',
        '91c0729e-6af5-445c-88ff-771efe85042f',
        '92da5e5b-a560-4aa9-a836-14c440ab48c5',
        '9405dc4f-e737-49b8-82b8-6065fc9b63d0',
        '952a4093-59cf-481e-a7be-8a66adcebdb0',
        '95909e5f-48eb-411b-951e-4e64d410ada0',
        '968557b2-780c-4ab1-b5c1-2a2c3480c00c',
        '98655cf9-9599-4fa0-b03d-e67c4f421bd6',
        '98c00396-8352-44ec-9f4b-e70b9d59013d',
        '98e5789d-f767-43b4-bcf6-122b3c1f1030',
        '991cc5ad-2233-4f92-a3e0-bbed8b7ef803',
        '99e06dbf-70bc-4239-b73f-badfd14ea880',
        '9bac5876-e538-4d7b-b2d4-6b45b8a91e59',
        '9ca8c645-6b62-4253-a945-752cbb088382',
        '9ee87d71-5bec-4f96-9755-88aecb979e3d',
        '9fd54e2a-2415-426a-aab3-a242517d80da',
        'a0a4046d-3ca3-4755-8b26-ac484d369bff',
        'a2b52459-c277-47b0-a500-77c3e88ed30e',
        'a54b96a9-2e68-401b-9ccd-050c7c11add0',
        'a7005551-9ade-4d76-ac63-20c9d0ddb2f4',
        'aa4e7117-3291-4f7f-bbbf-8c48c089c3aa',
        'ac623a21-01af-4893-96f1-911e90b3ae6e',
        'ad91cb39-352d-4df3-9969-398f8201422c',
        'ad942251-7214-4d45-b8fd-0410c4ba274e',
        'af9094b5-09e1-4db3-ab76-434e8301498e',
        'b2b42e32-509c-4b00-b070-855d5c48646a',
        'b5b2e4af-839f-4580-affb-325c578d31b0',
        'b6cbbec4-cdd1-4f02-8880-be5343480043',
        'b82ce188-a2b2-401b-8913-96696b9e0297',
        'baa14fe7-a5f4-41ff-80d4-72ada4e543a5',
        'bc382f70-62e9-41c1-97c9-e313dbf77c9a',
        'bd44b20e-fbba-4c0a-825d-675795c31c68',
        'bd7849ac-a3dc-4c7e-b36f-7d9b7be6f94e',
        'c0c77960-71b0-46ab-9b99-532538e4118f',
        'c17da978-ed26-47b6-b3ea-0ea94924063e',
        'c1b4c23d-0cc0-4240-bae9-5c07ef9b5fc1',
        'c29133d0-62d3-4be9-bc49-4664b30c5d95',
        'c5081d5f-fa98-488c-9046-8e930996bcf2',
        'c6bee333-b436-49c7-83f8-1316f9141c3c',
        'c7afe648-0f97-44de-998e-c718821a79fd',
        'c8b59303-9f88-45c2-8dc9-031e6dbb8842',
        'cd05e438-aa5d-4a18-8982-5ff9d55d2da0',
        'cd1f1902-cc78-4ebe-959e-618cdcaf79ac',
        'ce35fdd9-d314-4933-8136-7e6cff3603ad',
        'ceb175b1-3de0-4085-85a0-40a67ca7c8bd',
        'd6eb21bf-be10-4f54-8e8e-61a537951a5a',
        'd9a01347-76aa-4a50-9d6e-7f2fbefc3a8e',
        'db251705-7114-452c-b912-0ba2f1f80193',
        'dcb18067-5b2e-41ba-91e4-b7e760b08dc9',
        'dfc09fae-5603-41f7-a78b-96eb638a33c6',
        'e0d623f1-9854-4da8-a999-2c7f3b62b01b',
        'e16f3151-aa71-40ef-b403-b8f348ac0033',
        'e666533a-d6c3-412f-b0ec-95ff9e4b360b',
        'e66ba6d9-fad6-403f-84a5-39394d2ef875',
        'e7c0f662-840e-4321-8988-32ec794af56e',
        'e95316d8-d70f-4438-be50-dd3128f05d99',
        'e9816296-abb7-448e-887d-53906f3714f1',
        'e9963f1f-5f45-49c5-b8d9-e994243a046a',
        'eb1264f6-28c2-4612-af26-dc5f14ab81da',
        'eb2df252-826e-471b-b646-c50449dea8c0',
        'eb44af90-391b-4039-ad51-fbb52667642e',
        'ebfeb1dc-0c26-443c-b905-4c0556cb5120',
        'ec557572-03dc-4773-97a6-41c513aa3bf0',
        'ee287dce-ee8b-4abb-afc7-c9d1a5af5239',
        'eeba42a5-80dc-4264-8fc9-6ffdf6b394bc',
        'ef619e6b-cc90-4f75-b84e-6420d086d387',
        'ef74544a-8556-4f50-8a86-e9a7075abbe9',
        'f111b9e1-646a-41c8-9173-4eb098ef8027',
        'f4d38e80-51cc-4371-90f8-860bdcbe6e48',
        'f80a3409-13cb-479a-b053-427da8e1fe65',
        'f925432a-b574-4619-8abe-fbd1b5342f39',
        'fab6012d-891d-4be1-b0dd-7c50f0c6b722',
        'feaec1da-6860-4461-b8dd-9d0bee8cbb21',
        'ff393cdc-5c9e-4f38-874c-42c70b0d4c2e']

    # Test connectivity export
    '''data = split_pipeline(ids=ids, subfolder=False,
                          dir=os.path.join(hlp.DATA_DIR, 'appevents'),
                          time_range=time_range,
                          indices=(['connectivity']),
                          parquet=False,
                          csv_file=True)'''

    data = pipeline(ids=ids, subfolder=False,
                    name="implicit_new",
                    dir=os.path.join(hlp.DATA_DIR, 'implicit'),
                    time_range=time_range,
                    indices=(['appevents', 'notifications', 'sessions']),
                    parquet=False,
                    csv_file=True)
