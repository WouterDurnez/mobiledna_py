# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

BASIC ANALYSIS FUNCTIONS

-- Coded by Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import os
from pprint import PrettyPrinter

import pandas as pd

import mobiledna.basics.help as hlp
from mobiledna.basics.help import check_index

pp = PrettyPrinter(indent=4)


##################
# Appevents core #
##################

@hlp.time_it
def count_days(df: pd.DataFrame, overall=False) -> pd.Series:
    """
    Count number of count_days for which logs exist (per ID or overall)

    :param df: appevents data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: day count (Series)
    """

    # Check data frame type
    check_index(df=df, index='appevents', ignore_error=True)

    # Get date portion of timestamp and factorize (make it more efficient)
    df['startDate'] = pd.to_datetime(df['startTime'], unit='s').dt.date

    # If we're looking across the whole dataset, return the number of unique dates in the dataset
    if overall:
        return pd.Series(df.date.nunique(), index=['overall'])

    # ...else, get number of unique dates per ID
    return df.groupby(by=['id']).startDate.nunique()


@hlp.time_it
def count_events(df: pd.DataFrame, overall=False) -> pd.Series:
    """
    Count number of appevents (per ID or overall)

    :param df: appevents data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: count of appevents (Series).
    """

    # Check data frame type
    check_index(df=df, index='appevents', ignore_error=True)

    # If we're looking across the whole dataset, just return the length
    if overall:
        return pd.Series(len(df), index=['overall'])

    # ...else, get number of rows per ID
    return df.id.value_counts()


@hlp.time_it
def active_screen_time(df: pd.DataFrame, overall=False) -> pd.Series:
    """
    Count screen time spent on appevent activity (per ID or overall)

    :param df: appevents data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: appevent screen time (Series).
    """

    # Check data frame type
    check_index(df=df, index='appevents', ignore_error=True)

    # Check if duration column is there...
    if 'duration' not in df:
        # ...if it's not, add it
        df = hlp.add_duration(df=df)

    # If we're looking across the whole dataset, just return the length
    if overall:
        return pd.Series(df.duration.sum(), index=['overall'])

    # ...else, get total active screen time per ID
    return df.groupby(by=['id']).duration.sum()


#################
# Sessions core #
#################

@hlp.time_it
def count_sessions(df: pd.DataFrame, overall=False) -> pd.Series:
    """
    Count number of sessions (per ID or overall)

    :param df: sessions data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: count of sessions (Series)
    """

    # Check data frame type
    check_index(df=df, index='sessions', ignore_error=True)

    # Remove rows with deactivation
    df = df.loc[df['session on'] == True]

    # If we're looking across the whole dataset, just return the length
    if overall:
        return pd.Series(len(df), index=['overall'])

    # ...else, get number of rows per ID
    return df.id.value_counts()


@hlp.time_it
def screen_time(df: pd.DataFrame, overall=False) -> pd.Series:
    """
    Get overall screen time from sessions index (overall or per ID).

    :param df: sessions data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: screen time (Series)
    """
    # Check data frame type
    check_index(df=df, index='sessions', ignore_error=True)

    # Check if duration column is there...
    if 'duration' not in df:
        # ...if it's not, add it
        df = hlp.add_duration(df=df)

    # If we're looking across the whole dataset, just return the length
    if overall:
        return pd.Series(df.duration.sum(), index=['overall'])

    # ...else, get total active screen time per ID
    return df.groupby(by=['id']).duration.sum()


########
# MAIN #
########

if __name__ == "__main__":
    hlp.hi()

    df = hlp.load(path=os.path.join(hlp.DATA_DIR, "glance_small_appevents.parquet"), index='appevents')

    days = count_days(df, overall=True)
    days2 = count_days(df, overall=False)
    events = count_events(df, False)
    duration = active_screen_time(df, True)

    df.startTime.groupby('id').max()

    # test = screen_time(df)

    a = active_screen_time(df=df)
    # s = screen_time(df=ses)
