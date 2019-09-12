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
import random
import sys
from pprint import PrettyPrinter

import pandas as pd
from elasticsearch import Elasticsearch
import numpy as np
import mobiledna.communication.config as cfg

import mobiledna.basics.help as help

# Globals
pp = PrettyPrinter(indent=4)
fieldnames = {'appevents':
                  ['application',
                   'battery',
                   'data_version',
                   'endTime',
                   'endTimeMillis',
                   'id',
                   'latitude',
                   'longitude',
                   'model',
                   'notification',
                   'session',
                   'startTime',
                   'startTimeMillis'],
              'notifications':
                  ['id',
                   'notificationID',
                   'application',
                   'time',
                   'posted',
                   'data_version'],
              'sessions':
                  ['id',
                   'timestamp',
                   'session on',
                   'data_version'],
              'logs':
                  ['id',
                   'date',
                   'logging enabled']}
time_var = {
    'appevents': 'startTime',
    'notifications': 'time',
    'sessions': 'timestamp',
    'logs': 'date'
}
doc_types = {"appevents","notifications","sessions"}


#######################################
# Connect to ElasticSearch repository #
#######################################

def connect(server=cfg.server, port=cfg.port) -> Elasticsearch:
    """Establish connection with data"""

    es = Elasticsearch(
        hosts=[{'host': server, 'port': port}],
        timeout=100,
        max_retries=10,
        retry_on_timeout=True
    )
    return es


#############################################
# Functions to get ids (from server or file #
#############################################

def ids_from_file(dir='', file_name='ids', file_type='csv') -> list:
    """Read ids from file. Use this if you want to get data from specific
    users, and you have their listed their ids in a CSV file."""

    # Create path
    path = dir + ('/' if dir != '' else '') + file_name + '.' + file_type

    # Initialize id list
    id_list = []

    # Open file and read lines
    with open(path) as file:
        reader = csv.reader(file)
        for row in reader:
            id_list.append(row[0])

    return id_list


def ids_from_server(doc_type="appevents",
                    time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000')) -> dict:
    """Fetch ids from server. Returns dict of user ids and count.
    Can be based on appevents, sessions, or notifications."""

    # Check argument
    if doc_type not in doc_types:
        raise Exception("Must be based on appevents, sessions or notifications!")

    # Connect to es server.
    es = connect()

    # Log
    print("Getting ids that have logged {doc_type} between {start} and {stop}.".format(
        doc_type=doc_type, start=time_range[0], stop=time_range[1]))

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
        body['query'] = {
            'bool': {
                'filter':
                    range_restriction

            }
        }

    except:
        print("Failed to restrict range. Getting all data.")

    # Search using scroller (avoid overload)
    res = es.search(index="mobiledna",
                    body=body,
                    request_timeout=300,
                    # scroll='30s',  # Get scroll id to get next results
                    doc_type=doc_type)

    # Initialize dict to store ids in.
    ids = {}

    # Go over buckets and get count
    for b in res['aggregations']['unique_id']['buckets']:
        ids[b['key']] = b['doc_count']

    # Log
    print("-- Found {n} active ids.\n".format(n=len(ids)))

    return ids


def common_ids(doc_type="appevents",
               time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000')) -> (list, dict):

    """Which ids are present in all indices? Returns a list of common ids,
    as well as a restricted count of docs in given index."""

    ids = {}
    id_sets = {}

    # Go over most important indices (fuck logs, they're useless).
    for type in {"sessions", "notifications", "appevents"}:

        # Collect counts per id, per index
        ids[type] = ids_from_server(doc_type=type, time_range=time_range)

        # Convert to set so we can figure out intersection
        id_sets[type] = set(ids[type])

    # Calculate intersection of ids
    ids_inter = id_sets["sessions"] & id_sets["notifications"] & id_sets["appevents"]

    print("{n} ids were found in all indices.\n".format(n=len(ids_inter)))

    return list(ids_inter), {id: ids[doc_type][id] for id in ids_inter}


def richest_ids(ids: dict, top=100) -> dict:
    """Return ids with largest counts."""

    rich_ids = dict(sorted(ids.items(), key=lambda t: t[1], reverse=True)[:top])

    return rich_ids


def random_ids(ids: dict, n=100) -> list:
    """Return random sample of ids."""

    selection = {k: ids[k] for k in random.sample(population=ids.keys(), k=n)}

    return selection


###########################################
# Functions to get data, based on id list #
###########################################

def fetch(doc_type: str, ids: list, time_range=('2017-01-01T00:00:00.000', '2020-01-01T00:00:00.000')) -> dict:
    """Fetch data from server"""

    # Are we looking for the right doc_types?
    if doc_type not in doc_types:
        raise Exception("Can't fetch data for anything other than appevents,"
                        " notifications or sessions (or logs, but whatever).")

    # If there's more than one id, recursively call this function
    if len(ids) > 1:

        # Save all results in dict, with id as key
        dump_dict = {}

        # Go over ids and try to fetch data
        for index, id in enumerate(ids):

            print("ID {index}: \t{id}".format(index=index + 1, id=id))
            try:
                dump_dict[id] = fetch(doc_type=doc_type, ids=[id], time_range=time_range)[id]
            except:
                print("Fetch failed for {id}".format(id=id))

        return dump_dict

    # If there's one id, fetch data
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

def export_elastic(dir: str, name: str, doc_type: str, data: dict, subfolder=False, pickle=True, csv_file=False):
    """Export data to file type (standard pickle, csv possible)."""

    # Did we get data?
    if data is None:
        raise Exception("Received empty data. Failed to export.")

    # Gather data to write to CSV
    to_export = []
    for d in data.values():
        for dd in d:
            to_export.append(dd['_source'])

    # Export file to pickle
    df = pd.DataFrame(to_export)
    dir = "data/" + ((doc_type + "/") if subfolder else "") + name
    new_name = name + "_" + doc_type
    help.save(df=df, dir=dir, name=new_name, csv=csv, pickle=pickle)


##################################################
# Pipeline functions (general and split up by id #
##################################################

def pipeline(dir: str, name: str, ids: list,
             doc_types={"appevents","sessions", "notifications"},
             time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
             subfolder=False,
             pickle=True, csv_file=False):
    """Get all doc_types sequentially."""

    # All data
    all_df = {}

    # Go over interesting doc_types
    for doc_type in doc_types:
        # Get data from server
        print("\nGetting " + doc_type + "...\n")
        data = fetch(doc_type=doc_type, ids=ids, time_range=time_range)

        # Export data
        print("\n\nExporting " + doc_type + "...")
        export_elastic(dir=dir, name=name, doc_type=doc_type, data=data,
                       subfolder=subfolder, csv_file=csv_file, pickle=pickle)

        all_df[doc_type] = data

    print("\nDone!\n")

    return all_df


def split_pipeline(dir: str, name: str, ids: list,
                   time_range=('2018-01-01T00:00:00.000', '2020-01-01T00:00:00.000'),
                   subfolder=False,
                   pickle=True, csv_file=False):
    """Same pipeline, but split up for ids."""

    # Go over id list
    for id in ids:

        print("###########################################")
        print("# ID {} #".format(id))
        print("###########################################")

        pipeline(dir=dir + "/" + name,
                 name=id,
                 ids=[id],
                 time_range=time_range,
                 pickle=pickle,
                 subfolder=subfolder,
                 csv_file=csv_file)

    print("\nAll done!\n")


########
# MAIN #
########

if __name__ in ['__main__', 'builtins']:
    # Sup?
    help.hi()

    # Set time range
    time_range = ('2018-12-21T00:00:00.000', '2019-01-07T00:00:00.000')

    # Get common ids (standard count return: appevents)?
    #
    #ids, id_counts = common_ids(time_range=time_range)
    #id_counts = np.load("ids.npy").item()

    # Get top 1000 ids with richest data
    #ri = richest_ids(id_counts, top=10000)

    # ... or get 2000 random ids
    #rai = random_ids(id_counts, n=10)

    # Save as numpy
    #np.save("ids.npy", id_counts )

    # Save as json
    # with open('ids.json', 'w') as fp:
    #    json.dump(id_counts, fp=fp)

    # ids = list(np.load("ids.npy").item())[2700:]
    ids = [
        'a011f110-bd7a-49ca-8e0c-a3368e84cf12',
        '221d5890-6016-49be-93d6-d48786f77343',
        '8f29220e-e5f5-4ed1-b119-4c69ed2d552d',
        'ab8cd9fc-b5c4-4498-8bb5-cae2c644455b',
        '2c880184-0e55-4a17-a6c3-069c5c543046',
        '130d3a79-9b84-43c3-b279-5ddb3c1390d2',
        'ca87a761-3c38-4d4b-89ca-33e40bc76459',
        'b055b374-cd58-414b-8f89-f355e40f37b6',
        '51f7183c-9747-4984-b209-2abcef508601',
        '42899a37-f352-4b75-b20c-caf0792576e4',
        '92c5412e-2092-491a-8a41-7a43f3e9d6a3',
        'abed3030-4610-4c9d-b61b-de882855f0e4',
        '809986b4-0263-4c75-a0ab-0916d9e67a82',
        '37781c42-f379-4843-8d9a-075b66d3c2ca',
        '0a7cf995-f76d-4931-944e-724834cd8b28',
        '3cc6d6e4-b314-4390-8679-3f7680f6fece',
        '32172fad-7629-43a8-987c-cb6932b5eb23',
        '89498bba-08a2-454c-84bf-4fcc031e628c',
        'd1309fab-2e5a-4262-afe3-a6599287c8af',
        'aba8d1cd-4b85-4713-93e3-22da341d2348',
        '73cc7c36-64d9-4472-a4a7-47dc9bd055e4',
        '4fd8c9c0-4fd8-4115-954f-db431b966d72',
        '900e0643-7a26-4368-aab4-c2071674c51b',
        'e40adf17-5903-46d6-b9a1-ed2c8168c4fb',
        '64d77575-5618-4cc8-bc49-00b8370f3bdb',
        '0b40334c-8887-45fb-be9b-0068c6e4ad74',
        'c8724a2d-1b31-4286-830b-a2f4e8ab2cb5',
        '41be1b9d-ac88-4d73-8d4d-a557d3e4ee96',
        '19e36d90-d134-49e1-8313-83edb3d63651',
        '7891bc92-9877-4029-a7b1-a4a7d10fb577',
        '4dd127a4-5d67-4031-b388-1dbf2a15a2b9',
        'da912c23-dc29-4475-b76f-f657bf694b4b',
        'd59a2e84-c5e0-4fc7-969e-97aa7bdc366d',
        '64351c35-bb9b-41ee-913f-d1d1dc3c0080',
        'ebd9c215-7335-42d2-a53f-cc21fa45cd9a',
        '9953bccf-4a3e-4516-8a7a-586df0dc7532',
        '377503dc-51dc-49fb-a05e-f3fc3f58fd52',
        '1d795dbc-bb42-4b8d-89f4-25986be86c3a',
        'a45a1a8a-de1f-4987-b779-0de6d4c94e5b',
        'b47e8a6d-40ba-4677-8221-c19657cdd4fd',
        'ef4d1ad4-23e0-4b23-b8ea-8b7fec6c113c',
        '883ba17b-1461-45cf-99e8-b32b3284d5d0',
        'bce51fd8-f66f-435f-8b03-dcf7d63d8762',
        'f1a3eea3-3928-47bd-8faf-3cba35ff2aa2',
        '033a3406-e8e1-46a4-98d0-9a57daf42aa6',
        'eff6a252-0c09-423a-8804-cfc1e9f4e249',
        'af49d84f-2e85-4187-aa93-009d6d2cf4f7',
        'e1a2095c-42de-477f-bfc7-ba015155587b',
        'b3fdb9f9-815d-4743-bb6a-c45a180af1f9',
        '24897121-6712-4413-b02f-1900f5c28fa0',
        'a339e9a1-df7f-46c5-8e31-f9eadb9cf89f',
        '1663dce5-2fce-47d9-99da-00c924c1f8fb',
        '85473ce6-1c89-46df-93b8-2b9e0ff33e9b',
        'f6b9965f-312a-44e8-a54c-ea16242894fa',
        'f091e63c-4e38-471c-80c5-24d794760fc1',
        '1dd6d476-9fbd-4549-91a1-d956e88ec3ef',
        '82f81bd4-f78b-4ec2-b79c-8980df8cd71b',
        '29fb9583-4863-4018-b35d-4237349dfae6',
        '48b436de-466c-45d4-ad99-7d80c0491d0f',
        'f3214263-3140-4687-bd61-1fbc68623b3f',
        'd4f27be1-a82f-4041-999b-a59ae3741272',
        '643bce07-daa1-409a-853f-7615a919061a',
        '8e793924-b02f-4521-affe-59a78a33d557',
        'ea4a945d-d6ab-4daa-b743-721b06691158',
        'b948c08a-903f-4c90-ac3a-58c5ccf8aaa0',
        '1201c8b4-6a0b-45f0-ac63-04b258d6d668',
        'e1638983-b058-4b3e-8396-484ecadc7e18',
        'df17c3d4-329b-4783-8e1c-cee351a67dae',
        '4d5dba83-8a1a-4a47-8103-c167b9577eb1',
        '52d681e2-3432-4d25-9049-e0044648e8e4',
        '5cae09fc-81c6-4709-986e-16d32fc84d8d',
        '6218eb8b-dfa4-42c1-be74-c96792010034',
        '1862d0ff-e739-4eda-90e7-ef40f8d1b66a',
        '13bf4ab8-7c18-4258-93e1-f202efba85ec',
        'bddeebaa-3bbf-4da6-895c-cf935cd3bf25',
        'd87113eb-e726-4bff-8014-8f709e02bd88',
        'e02e44e4-2532-4a4b-8db6-d77d56719f6e',
        '78859336-bcfb-402a-885b-7f9c52b24263',
        'c36ee3f0-6304-41cc-9d90-2cded6529be6',
        'e93cf518-dd06-427e-8a37-7b55f332242e',
        'ad4eb64f-1a4a-462a-9f3b-b20cc138bcfb',
        '123d2500-6e21-4866-8ecc-358ecf5b3ae8',
        '880c1a5a-1a71-487b-a74e-668d1c6f943b',
        'd3099aa5-f0d0-416c-95cd-812ad4beb84c',
        '5891fed9-9900-4caf-b0c5-3c23eb939e7a',
        '12efa7c1-14af-4a50-ad7d-10d76c77af92',
        '3a0e74c7-f130-4926-a1be-8c07b2de7d91',
        '5a8b44da-0b57-47fd-b735-9f7c2fdc5355',
        '61783727-50ed-4514-9c38-de5714559f69',
        '6fefe6b6-0beb-408b-8e60-221f8e559337',
        '30ac99ab-7783-4998-afd1-c7fe6db56e75',
        '19456d40-affb-4459-bd8f-113227566833',
        'f29e3bf2-8b9a-48a5-a83f-dcff88fe9b70',
        '025a9d5a-8728-434d-9de6-9c263e7bf5cc',
        '6c6f9678-334f-44d7-8131-65d7cb620f27',
        'c349037f-133d-47a4-ae98-84a8422e61af',
        '130f026a-7f84-4568-be39-50457f0efba4',
        '3d89a686-508c-4840-9dae-1db768b7122d',
        'ee5ed113-2553-497b-9a4c-9249b78e169e',
        'c5e1fe6d-795a-4b88-9d5f-ddabd29181cd',
        '25c2a8d3-f300-4412-85ed-a6f3eb80d960',
        'eeca5217-6b2c-4c58-a283-08f696eb3b9f',
        'ae2f9f0d-a62a-4c28-b991-a806c6122669',
        '7ada0f23-d917-44c1-b56f-54f2e31455f4',
        '951da2ec-8586-4cfd-bdba-ff4800e27855',
        '88f7541e-c706-4d2d-9ef4-e0e0124e07ff',
        '1e3bca7b-20da-4c57-8deb-2f4f331d46f2',
        'cbb98c37-2000-4447-88d8-95ea0bb6d6ea',
        '76467169-13ce-4dc3-94d8-ab01ed32307d',
        'e9b9d42b-f50b-47ae-851b-ed2b10a5c125',
        '61653ed2-945b-4881-8f67-3848634b4c78',
        '21c787b0-6b58-4f35-8501-5456319485ee',
        'f0f605de-b6eb-44ad-b7ff-58443324b9aa',
        'b05699e5-c304-42f0-8f55-7882daa29a61',
        'acf1e258-a8e7-4b26-81b3-78ff2d6682ab',
        '587a6788-7c10-4292-b8fa-d24a49a2c4d6',
        '2d44ec01-9ded-4983-9d32-1984b133ac3c',
        'c0e8d169-a1ec-4e32-93ed-a88a05af90a5',
        '7dd35604-ea3a-4290-90de-b138a64d6493',
        '289635c8-f360-4da5-8d00-54368825218f',
        'bb44b98f-f10f-4367-ba5c-879e1a7b9c40',
        'a3ec8629-7692-4dd0-8f0b-52c87b98810a',
        '597bcee5-e2dd-4667-9daa-3523b2dd45d5',
        '4bde1cdf-655f-44af-aa27-8f73656c4a86',
        'e7b5ebce-32eb-411e-be35-a819472679f8',
        'deb5c7b0-2e47-410e-a41b-e49cbabb3a58',
        '384642a7-7f05-4832-abe1-e9e9f94c7e74',
        'd39c70f0-f5a5-453c-9f97-9a033c61a352',
        'fdf5c101-c62c-4831-a048-7a28717d420c',
        'b8df77de-7200-48c0-8af8-7601bc5bff98',
        'bdcf3899-e570-408d-beeb-dbd59c5aa421',
        'a485f2d4-ebeb-4dcb-8919-dee1f258954d',
        '03d38870-2018-49e1-a0b7-d934de9ae6af',
        '4c7d0977-1652-434a-a2fc-5973e8691189',
        'd1a27545-0935-4a79-aa91-2fbf7b6c5112',
        'bac5ff98-ae67-49fa-a7ea-2e286ff6d5ef',
        '183a1637-7053-4c24-9889-98afabaa849d',
        '4b3c59a7-6b06-459c-8e41-6a58c1bb819f',
        '5feb784f-36f5-420c-a36e-530446b9ea5d',
        '844254bb-52eb-4265-9548-fb2dad679657',
        '1ea135a6-45ba-4c8d-a33e-b4c84d5f7d45',
        'f3d282d8-1be9-4cde-aa37-21e4dbacd77b',
        'f4295891-111e-4c4f-b077-a2672b64e04d',
        '2b19168e-f774-49c7-9c1b-391e90cce26e',
        '6735652b-24d0-484f-b61f-fa7196b9b8c2',
        '808b2f6c-2186-42e6-ab9c-7238abf2ecb3',
        '8e565053-f0e8-45cd-b47e-b9c6c2452ae0',
        '73395f59-a3d3-4c75-9ba3-c70cc05f4879',
        '6d706576-9aba-4644-aab1-12109eb1296f',
        '54401e10-3ace-4ad0-8717-27685d89a3cb',
        '11159c15-a951-4219-850d-c33768509b01',
        '00a0557a-5e7c-4476-a393-71e12a458ee3',
        '28d4829d-8dd3-41a8-9de3-e33a469d943a',
        '441a949b-7d7b-42fb-a177-1a543024984d',
        'e13fb118-f128-49d8-8123-2209d3b6fdb6',
        'cb052eca-2822-473e-92ba-eaf14df0e7f6',
        '26ddf803-8bad-4417-9a3b-c9c26418af1a',
        'fc6cd6f0-6f3d-488f-b1fa-83dc6925ce06',
        '99f4fbcc-8b0d-461d-bc03-b7e8d4ab4331',
        'f9b010d8-45b9-498f-a465-b6355cbdd7e3',
        '4be7559a-d480-467a-a037-8a0dd1eac905',
        'ad10c0b1-a56e-493c-90a9-e80aa4c287e3',
        '58f0ddae-c0d7-406c-aa35-5276cc7f5bdb',
        'c71ac058-33f1-4589-ad48-3a636618ad1d',
        'debaa6e1-4f56-49ff-80bb-04a871fd27da',
        '6e734096-8ff1-401a-a214-9e2db076753a',
        '17ff522a-c067-47e0-8f66-42e6a296820f',
        'f144b946-c732-4a22-9f09-ac5186c77fef',
        '3b3781c2-4ab0-49cb-b0ef-f70a9a639a8e',
        '3fa1206b-f4d9-4912-8d06-c91fd166d88a',
        '4a064e9c-d736-4d7b-b9f6-a2cf38eb0b6b',
        '90b6f485-ffab-49d1-a63a-d19f35d22edd',
        '9c8d6414-26b9-42a1-bc0d-7003ce7bf06c',
        'a71b62e4-b186-4f47-8069-9a9eb2f38dfe',
        'd26739d0-063f-4d6a-9e49-1ac92bfd6ff1',
        'd66e6e0c-87f8-49d4-a1e9-1b5c9204c2d2',
        '91c3ad5b-8147-4915-8601-af51fea27c42',
        '76b79f7c-2dfe-4e75-998b-6e91b75f519a',
        'eff80c84-f37b-4605-a518-72c7df8f6c2c',
        '0fa07fd7-7df5-434c-96f6-c98d7e1b2ea8',
        'c0047a9b-d148-4440-ae68-a110d4f16649',
        '28994ecd-ab49-4805-80b3-1039d4a71878',
        '870690f7-1eea-4a13-96ea-ed36ea896735',
        '735ba30f-cb33-453a-9795-c26959843825',
        '283b44e5-0fd5-4f26-8a62-ca311215c82d',
        'c08f55f9-57f3-4b2c-9e70-65a1b2f81e99',
        '41b50f53-a153-4a03-87e7-0ce12bc7bdf0',
        'e80372a6-ffd8-449c-a410-4eb8afac9787',
        'dc15fba7-ed71-40c0-b80d-469151cebfec',
        'd511d72d-1356-4115-803f-2687138fba60',
        '698a35f8-8f00-4572-a0f4-cffb6bc70f96',
        'de43b37d-ec37-46e5-92b2-a7da23d55930',
        'b7dd1220-63ba-458a-af30-dfe10a5f1362',
        'cc987af8-524b-49c4-80fb-251e564678'
    ]

    # Get data (file per id)
    '''plit_pipeline(
        dir="data",
        name="core",
        ids=ids,
        time_range=time_range,
        subfolder=True,
        pickle=True,
        csv_file=False
    )'''

    # Get data (single file)
    pipeline(
        dir="data/190329_siam1/",
        name="siam1",
        ids=ids,
        time_range=time_range,
        pickle=False,
        csv_file=True
    )