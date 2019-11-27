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
import random as rnd
import time
from datetime import datetime
from pprint import PrettyPrinter
from typing import Callable

import numpy as np
import pandas as pd

pp = PrettyPrinter(indent=4)
indices = {'notifications', 'appevents', 'sessions', 'logs'}
index_fields = {
    'notifications': [
        'application',
        'data_version',
        'id',
        'notificationID',
        'ongoing',
        'posted',
        'priority',
        'studyKey',
        'surveyId',
        'time'],
    'appevents': [
        'application',
        'battery',
        'data_version',
        'endTimeMillis',
        'id',
        'latitude',
        'longitude',
        'model',
        'notification',
        'notificationId',
        'session',
        'startTimeMillis',
        'studyKey',
        'surveyId'
    ],
    'sessions': [
        'data_version',
        'id',
        'session on',
        'studyKey',
        'surveyId',
        'timestamp'
    ],
    'logs': [
        'data_version',
        'id',
        'studyKey',
        'surveyId',
        'logging enabled',
        'date'
    ]
}

####################
# GLOBAL VARIABLES #
####################

# Set log level (1 = only top level log messages -> 3 = all log messages)
LOG_LEVEL = 3
DATA_DIR = os.path.join(os.pardir, os.pardir, 'data')


####################
# Helper functions #
####################

def set_param(log_level=None, data_dir=None):
    """
    Set mobileDNA parameters.

    :param log_level: new value for log level
    :param data_dir: new data directory
    """

    # Declare these variables to be global
    global LOG_LEVEL
    global DATA_DIR

    # Set log level
    if log_level:
        LOG_LEVEL = log_level

    # Set new data directory
    if data_dir:
        DATA_DIR = data_dir


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


def time_it(f: Callable):
    """
    Timer decorator: shows how long execution of function took.
    :param f: function to measure
    :return: /
    """

    def timed(*args, **kwargs):
        t1 = time.time()
        res = f(*args, **kwargs)
        t2 = time.time()

        log("\'", f.__name__, "\' took ", round(t2 - t1, 3), " seconds to complete.", sep="")

        return res

    return timed


def set_dir(*dirs):
    """
    If folders don't exist, make them.

    :param dirs: directories to check/create
    :return: None
    """

    for dir in dirs:
        if not os.path.exists(os.path.join(os.pardir, dir)):
            os.makedirs(os.path.join(os.pardir, dir))
            log("WARNING: Data directory <{dir}> did not exist yet, and was created.".format(dir=dir), lvl=1)
        else:
            log("\'{}\' folder accounted for.".format(dir), lvl=3)


def split_time_range(time_range: tuple, duration: pd.Timedelta, ignore_error=False) -> tuple:
    """
    Takes a time range (formatted strings: '%Y-%m-%dT%H:%M:%S.%f'), and selects
    a random interval within these boundaries of the specified duration.

    :param time_range: tuple with formatted time strings
    :param duration: timedelta specifying the duration of the new interval
    :return: new time range
    """

    # Convert the time range strings to unix epoch format
    start = datetime.strptime(time_range[0], '%Y-%m-%dT%H:%M:%S.%f').timestamp()
    stop = datetime.strptime(time_range[1], '%Y-%m-%dT%H:%M:%S.%f').timestamp()

    # Calculate total duration (in seconds) of original
    difference = stop - start

    # Calculate duration of new interval (in seconds)
    duration = duration.total_seconds()

    # Error handling
    if difference < duration:

        if ignore_error:
            log("WARNING: New interval length exceeds original time range duration! Returning original time range.")
            return time_range

        else:
            raise Exception('ERROR: New interval length exceeds original time range duration!')

    # Pick random new start and stop
    new_start = rnd.randint(int(start), int(stop - duration))
    new_stop = new_start + duration

    # Format new time range
    new_time_range = (datetime.fromtimestamp(new_start).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
                      datetime.fromtimestamp(new_stop).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])

    return new_time_range


############################
# Initialization functions #
############################

def hi():
    """Say hello. (It's stupid, I know.)
    If there's anything to initialize, do so here."""

    print("\n")
    print("    __  ___      __    _ __     ____  _   _____ ")
    print("   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |")
    print("  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |")
    print(" / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |")
    print("/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|")
    print("\n")

    print("LOG_LEVEL is set to {}.".format(LOG_LEVEL))
    print("DATA_DIR is set to {}".format(DATA_DIR))
    print()

    # Set this warning if you intend to keep working on the same data frame,
    # and you're not too worried about messing up the raw data.
    pd.set_option('chained_assignment', None)


########################
# Data frame functions #
########################

def format_data(df: pd.DataFrame, index: str) -> pd.DataFrame:
    """
    Set the data types of each column in a data frame, depending on the index.
    This is done to save memory.

    :param df: data frame to format
    :param index: type of data
    :return: formatted data frame
    """

    # Check if index is valid
    if index not in indices:
        raise Exception("ERROR: Invalid doc type! Please choose 'appevents', 'notifications', 'sessions', or 'logs'.")

    elif index == 'appevents':

        # Reformat data version (trying to convert to int)
        df.data_version = pd.to_numeric(df.data_version, downcast='float')

        # Downcast timestamps
        df.startTimeMillis = pd.to_numeric(df.startTimeMillis, downcast='unsigned')
        df.endTimeMillis = pd.to_numeric(df.endTimeMillis, downcast='unsigned')

        # Downcast lat/long
        df.latitude = pd.to_numeric(df.latitude, downcast='float')
        df.longitude = pd.to_numeric(df.longitude, downcast='float')

        # Downcast battery column
        df.battery = df.battery.astype('uint8')

        # Factorize categorical variables (ids, apps, session numbers, etc.)
        df.id = df.id.astype('category')
        df.application = df.application.astype('category')
        df.session = df.session.astype('category')
        df.studyKey = df.studyKey.astype('category')
        df.surveyId = df.surveyId.astype('category')
        df.model = df.model.astype('category')

    elif index == 'notifications':

        df['time'] = pd.to_datetime(df['time'])

    elif index == 'sessions':

        df['timestamp'] = pd.to_datetime(df['timestamp'])

    elif index == 'logs':

        df['date'] = pd.to_datetime(df['date'])

    for col in df.columns:

        if col.startswith('Unnamed') or col not in index_fields[index]:
            df.drop(labels=[col], axis=1, inplace=True)

    return df


def add_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate app event duration and add to (new) data frame.

    :param df: data frame to process (should be appevents index)
    :return: modified data frame
    """

    if 'startTimeMillis' not in df.columns or \
            'endTimeMillis' not in df.columns:
        raise Exception("ERROR: Necessary columns missing!")

    try:
        df['duration'] = df['endTimeMillis'] - df['startTimeMillis']
    except:
        raise Exception("ERROR: Failed to calculate duration!")

    # Check if there are any negative durations.
    if not df[df["duration"] < 0].empty:
        raise Warning("WARNING: encountered negative duration!")

    return df


def save(df: pd.DataFrame, dir: str, name: str, csv_file=True, pickle=False):
    """
    Wrapper function to save mobileDNA data frames.

    :param df: data to store on disk
    :param dir: location to store it in
    :param name: name of the file
    :param csv_file: save in CSV format (bool)
    :param pickle: save in pickle format (bool)
    :return: /
    """

    path = os.path.join(dir, name)

    # Store to CSV
    if csv_file:

        # Try and save it
        try:

            df.to_csv(path_or_buf=path + ".csv", sep=";", decimal='.')

            log("Saved data frame to {}".format(path + ".csv_file"))

        except Exception as e:

            log("Failed to store data frame! - ", e, lvl=1)

    # Store to pickle
    if pickle:

        try:

            df.to_pickle(path=path + ".pkl")
            log("Saved data frame to {}".format(path + ".pkl"))

        except Exception as e:

            log("WARNING: Failed to store data frame! {e}".format(e=e), lvl=1)


def load(path: str, index: str, file_type="csv", sep=";", dec='.') -> pd.DataFrame:
    """
    Wrapper function to load mobileDNA data frames.

    :param path: location of data frame
    :param index: type of mobileDNA data
    :param file_type: file type (currently: cvs or pickle).
    :param sep: field separator
    :param dec: decimal symbol
    :return: data frame
    """

    # Check if index is valid
    if index not in indices:
        raise Exception("Invalid doc type! Please choose 'appevents', 'notifications', 'sessions', or 'logs'.")

    # Load data frame, depending on file type

    # CSV
    if file_type == "csv":
        df = pd.read_csv(filepath_or_buffer=path,
                         # usecols=,
                         sep=sep, error_bad_lines=False)

    # Pickle
    elif file_type == "pickle":
        df = pd.read_pickle(path=path)

    # ... add new file types here (e.g., parquet?)

    # Unknown
    else:
        raise Exception("ERROR: You want me to read what now? Invalid file type! ")

    # If there's nothing there, just go ahead and return the empty df
    if df.empty:
        return df

    # Go over different indices and format columns where necessary
    df = format_data(df=df, index=index)

    if 'duration' not in df:
        add_duration(df)

    return df


def get_unique(column: str, df: pd.DataFrame) -> np.ndarray:
    """
    Get list of unique column values in given data frame.

    :param column: column to sift through
    :param df: data frame to look in
    :return: unique values in given column
    """

    try:
        unique_values = df[column].unique()
    except:
        raise Exception("ERROR: Could not find variable {column} in dataframe.".format(column=column))

    return unique_values


########
# MAIN #
########

if __name__ in ['__main__', 'builtins']:
    # Howdy
    hi()

    df = load(path="../../../data/191120_lfael_appevents.csv", index='appevents')

    df.info(verbose=False)
