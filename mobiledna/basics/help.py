# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

HELPER FUNCTIONS

-- Coded by Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import os
import time
from pprint import PrettyPrinter

import numpy as np
import pandas as pd

pp = PrettyPrinter(indent=4)
doc_types = {"notifications", "appevents", "sessions", "logs"}


####################
# GLOBAL VARIABLES #
####################

# Set log level (1 = only top level log messages -> 3 = all log messages)
LOG_LEVEL = 1


#############
# FUNCTIONS #
#############

def log(*message, lvl=3, sep="", title=False):
    """
    Print wrapper that adds timestamp, and can be used to toggle levels of logging info.

    :param message: message to print
    :param lvl: importance of message: level 1 = top importance, level 3 = lowest importance
    :param sep: separator
    :param title: toggle whether this is a title or not
    :return: /
    """

    # Set timezone
    if 'TZ' not in os.environ:
        os.environ['TZ'] = 'Europe/Amsterdam'
        time.tzset()

    # Title always get shown
    lvl = 1 if title else lvl

    # Print if log level is sufficient
    if lvl <= LOG_LEVEL:

        # Print title
        if title:
            n = len(*message)
            print('\n' + (n + 4) * '#')
            print('# ', *message, ' #', sep='')
            print((n + 4) * '#' + '\n')

        # Print regular
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(str(t), (" - " if sep == "" else "-"), *message, sep=sep)

    return


def time_it(f):
    """Timer decorator: shows how long execution of function took."""

    def timed(*args, **kwargs):
        t1 = time.time()
        res = f(*args, **kwargs)
        t2 = time.time()

        log("\'", f.__name__, "\' took ", round(t2 - t1, 3), " seconds to complete.", sep="")

        return res

    return timed


def make_folders(*folders):
    """
    If folders don't exist, make them.

    :param folders:
    :return: None
    """

    for folder in folders:
        if not os.path.exists(os.path.join(os.pardir, folder)):
            os.makedirs(os.path.join(os.pardir, folder))
            log("Created \'", folder, "\' folder.", lvl=3)
        else:
            log("\'{}\' folder accounted for.".format(folder), lvl=3)


############################
# Initialization functions #
############################

def hi():
    """Say hello. (It's a stupid function, I know.)"""
    print("\n")
    print("    __  ___      __    _ __     ____  _   _____ ")
    print("   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |")
    print("  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |")
    print(" / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |")
    print("/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|")
    print("\n")

    pd.set_option('chained_assignment', None)


########################
# Data frame functions #
########################

def load(path: str, doc_type: str, file_type="csv", sep=";") -> pd.DataFrame:
    """Just a reading wrapper to load data frames."""

    # Check if doc_type is valid
    if doc_type not in doc_types:
        raise Exception("Invalid type!")

    # Load data frame, depending on file type
    if file_type=="csv":
        df = pd.read_csv(filepath_or_buffer=path, sep=sep, error_bad_lines=False)
    elif file_type=="pickle":
        df = pd.read_pickle(path=path)
    else:
        raise Exception("You want me to read what now?")

    # If there's nothing there, just go ahead and return the empty df
    if df.empty:

        return df

    # Go over different doc_types and format columns where necessary
    if doc_type == "appevents":

        df['endTime'] = pd.to_datetime(df['endTime'])
        df['startTime'] = pd.to_datetime(df['startTime'])

        if 'duration' not in df:
            add_duration(df)

        df["duration"] = pd.to_timedelta(df["duration"])

    elif doc_type == "sessions":

        df['timestamp'] = pd.to_datetime(df['timestamp'])

    elif doc_type == "notifications":

        df['time'] = pd.to_datetime(df['time'])

    return df


def load_all(dir: str,
             doc_types=("notifications","appevents","sessions"),
             file_type="csv") -> dict:
    """Load pickle or csv data into dataframes, and merge them."""

    # Put the data here
    data = {}

    # Go over types of data we wish to load
    for doc_type in doc_types:

        t1 = time.time()

        # Store data separately based on doc_type
        data[doc_type] = {}

        # Look for files in corresponding folders
        for file in os.listdir(dir + doc_type):

            # Get id (first part of file name)
            id = file.split(sep="_")[0]
            path = dir + doc_type + "/" + file

            df = load(path=path, doc_type=doc_type, file_type=file_type)

            if not df.empty:

                data[doc_type][id] = df

        t2 = time.time()

        print("-- Got {doc_type} in {time} seconds.".format(doc_type=doc_type, time=round(t2 - t1, 2)))

    return data


def add_duration(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate app event duration and add to (new) data frame."""

    try:
        df['duration'] = pd.to_datetime(df["endTime"]) - pd.to_datetime(df["startTime"])
        df["duration_s"] = df.apply(lambda row: row["duration"].total_seconds(), axis=1)
    except:
        raise Exception("Could not calculate duration!")

    # Check if there are any negative durations by comparing with duration 0.
    if not df[df["duration"] < pd.Timedelta(0)].empty:
        print("WARNING: encountered negative duration!")

    return df


def get_unique(column: str, df: pd.DataFrame) -> np.ndarray:
    """Get list of unique column values in given data frame."""

    # Checking if df has necessary column
    if column not in df.columns:
        print("Could not find variable {column} in dataframe - terminating script\n".format(column=column))
        return np.nan

    else:
        unique_values = df[column].unique()
        return unique_values


def save(df:pd.DataFrame, dir: str, name: str, csv=True, pickle=False):
    """Save a data frame as a csv file or pickle."""

    path = os.path.join(dir, name)

    if csv:
        try:
            df.to_csv(path_or_buf=path + ".csv", sep=";")
            print("Saved dataframe to {}".format(path + ".csv"))
        except Exception as e:
            print("Failed to store dataframe! - ", e)

    if pickle:
        try:
            df.to_pickle(path=path + ".pkl")
            print("Saved data frame to {}".format(path + ".pkl"))
        except Exception as e:
            print("Failed to store data frame! - ", e)

    print()


########
# MAIN #
########

if __name__ in ['__main__', 'builtins']:

    # Howdy
    hi()

