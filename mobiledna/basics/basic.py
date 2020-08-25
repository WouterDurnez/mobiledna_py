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

from os.path import join
from pprint import PrettyPrinter

import pandas as pd

import mobiledna.basics.help as hlp
from mobiledna.basics.help import check_index

pp = PrettyPrinter(indent=4)


##################
# Appevents core #
##################

@hlp.time_it
def count_days(df: pd.DataFrame, index='appevents') -> pd.Series:
    """
    Count number of count_days for which logs exist

    :param df: appevents __data__ frame
    :return: day count (Series)
    """

    # Check __data__ frame type
    check_index(df=df, index=index, ignore_error=True)

    if index in ('appevents', 'sessions'):
        df['startDate'] = pd.to_datetime(df['startTime'], unit='s').dt.date

        # Get number of unique dates per ID
        return df.groupby(by=['id']).startDate.nunique()

    elif index == 'notifications':
        df['date'] = pd.to_datetime(df['time'], unit='s').dt.date

        # Get number of unique dates per ID
        return df.groupby(by=['id']).startDate.nunique()


@hlp.time_it
def count_events(df: pd.DataFrame) -> pd.Series:
    """
    Count number of appevents

    :param df: appevents __data__ frame
    :return: count of appevents (Series).
    """

    # Check __data__ frame type
    check_index(df=df, index='appevents', ignore_error=True)

    # Get number of rows per ID
    return df.id.value_counts()


@hlp.time_it
def active_screen_time(df: pd.DataFrame) -> pd.Series:
    """
    Count screen time spent on appevent activity

    :param df: appevents __data__ frame
    :return: appevent screen time (Series).
    """

    # Check __data__ frame type
    check_index(df=df, index='appevents', ignore_error=True)

    # Check if duration column is there...
    if 'duration' not in df:
        # ...if it's not, add it
        df = hlp.add_duration(df=df)

    # Get total active screen time per ID
    return df.groupby(by=['id']).duration.sum()


#################
# Sessions core #
#################

@hlp.time_it
def count_sessions(df: pd.DataFrame) -> pd.Series:
    """
    Count number of sessions

    :param df: sessions __data__ frame
    :return: count of sessions (Series)
    """

    # Check __data__ frame type
    check_index(df=df, index='sessions', ignore_error=True)

    # Remove rows with deactivation
    df = df.loc[df['session on'] == True]

    # Get number of rows per ID
    return df.id.value_counts()


@hlp.time_it
def screen_time(df: pd.DataFrame) -> pd.Series:
    """
    Get overall screen time from sessions index

    :param df: sessions __data__ frame
    :return: screen time (Series)
    """
    # Check __data__ frame type
    check_index(df=df, index='sessions', ignore_error=True)

    # Check if duration column is there...
    if 'duration' not in df:
        # ...if it's not, add it
        df = hlp.add_duration(df=df)

    # .Get total active screen time per ID
    return df.groupby(by=['id']).duration.sum()


########
# MAIN #
########

if __name__ == "__main__":
    hlp.hi()
    hlp.set_param(log_level=3, data_dir='../../__data__/glance/appevents')
    df = hlp.load(path=join(hlp.DATA_DIR, '0a48d1e8-ead2-404a-a5a2-6b05371200b1_appevents.parquet'), index='appevents')

    df = hlp.add_dates(df, index='appevents')

    days = count_days(df)
    days2 = count_days(df)
    events = count_events(df)
    duration = active_screen_time(df)

    df.startTime.groupby('id').max()

    # test = screen_time(df)

    a = active_screen_time(df=df)
    # s = screen_time(df=ses)
