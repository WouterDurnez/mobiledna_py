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

pp = PrettyPrinter(indent=4)


########
# Core #
########

@hlp.time_it
def days(df: pd.DataFrame, overall=False) -> pd.Series:
    """
    Count number of days for which logs exist (per ID or overall)

    :param df: appevents data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: day count (Series)
    """

    # Get date portion of timestamp and factorize (make it more efficient)
    df['date'] = pd.to_datetime(df['startTimeMillis'], unit='ms').dt.date

    # If we're looking across the whole dataset, return the number of unique dates in the dataset
    if overall:
        return pd.Series(df.date.nunique(), index=['overall'])

    # ...else, get number of unique dates per ID
    return df.groupby(by=['id']).date.nunique()


@hlp.time_it
def events(df: pd.DataFrame, overall=False) -> pd.Series:
    """Count number of appevents (per ID or overall)

    :param df: Appevents data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: Count (Series)."""

    # If we're looking across the whole dataset, just return the length
    if overall:
        return pd.Series(len(df), index=['overall'])

    # ...else, get number of rows per ID
    return df.id.value_counts()


@hlp.time_it
def duration(df: pd.DataFrame, overall=False) -> pd.Series:
    """Count number of appevents (per ID or overall)

    :param df: Appevents data frame
    :param overall: (bool) across dataset (True) or per ID (False, default)
    :return: Count (Series)."""

    # If we're looking across the whole dataset, just return the length
    if overall:
        return pd.Series(df.duration.sum(), index=['overall'])

    # ...else, get total duration per ID
    return df.groupby(['id']).duration.sum()


if __name__ == "__main__":
    hlp.hi()
    path = os.path.join(hlp.DATA_DIR, 'appevents', 'test_appevents.csv')

    df = hlp.load(path=path, index='appevents', file_type='csv')

    days = days(df, overall=True)
    events = events(df, True)
    duration = duration(df, True)
