# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

SESSIONS CLASS

-- Coded by Kyle Van Gaeveren & Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import pandas as pd
import pickle
from tqdm import tqdm

import mobiledna.core.help as hlp
from mobiledna.core.annotate import add_category, add_date_annotation, add_time_of_day_annotation
from mobiledna.core.appevents import Appevents
from mobiledna.core.help import log

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Sessions:

    def __init__(self, data: pd.DataFrame = None):

        # Set dtypes #
        ##############

        # Set datetimes
        try:
            data.startTime = data.startTime.astype('datetime64[ns]')
        except Exception as e:
            print('Could not convert startTime column to datetime format: ', e)
        try:
            data.endTime = data.endTime.astype('datetime64[ns]')
        except Exception as e:
            print('Could not convert endTime column to datetime format.', e)

        # Set data attribute
        self.__data__ = data

        # Add duration columns
        self.__data__  = hlp.add_duration(df=self.__data__ )

        # Add date columns
        self.__data__ = hlp.add_dates(df=self.__data__, index='sessions')


    @classmethod
    def load_data(cls, path: str, file_type='infer', sep=',', decimal='.'):
        """
        Construct Sessions object from path to data

        :param path: path to the file
        :param file_type: file extension (csv, parquet, or pickle)
        :param sep: separator for csv files
        :param decimal: decimal for csv files
        :return: Sessions object
        """

        data = hlp.load(path=path, index='sessions', file_type=file_type, sep=sep, dec=decimal)

        return cls(data=data)

    @classmethod
    def from_pickle(cls, path: str):
        """
        Construct an Sessions object from pickle
        :param path: path to file
        :return: Sessions object
        """

        with open(file=path, mode='rb') as file:
            object = pickle.load(file)
        file.close()

        return object

    def save_data(self, dir: str, name: str, csv=False, pickle=False, parquet=True):
        """
        Save data from Sessions object to data frame
        :param dir: directory to save
        :param name: file name
        :param csv: csv format
        :param pickle: pickle format
        :param parquet: parquet format
        :return: None
        """

        hlp.save(df=self.__data__, dir=dir, name=name, csv_file=csv, pickle=pickle, parquet=parquet)

    def to_pickle(self, path: str):
        """
        Store an Sessions object to pickle
        :param path: path to file
        :return: None
        """

        with open(file=path, mode='wb') as file:
            pickle.dump(self, file, pickle.HIGHEST_PROTOCOL)
        file.close()

    def merge(self, *sessions: pd.DataFrame):
        """
        Merge new data into existing Session object.

        :param sessions: data frame with sessions
        :return: new Sessions object
        """

        new_data = pd.concat([self.__data__, *sessions], sort=False)
        new_data.drop_duplicates(inplace=True)

        return Sessions(data=new_data)

    def add_date_type(self, date_cols='date', holidays_separate=False):

        self.__data__ = add_date_annotation(df=self.__data__, date_cols=date_cols, holidays_separate=holidays_separate)

        return self

    def add_time_of_day(self, time_col='startTime'):

        self.__data__ = add_time_of_day_annotation(df=self.__data__, time_cols=time_col)

        return self

    def filter(self, users=None, day_types=None, time_of_day=None,
               inplace=False):

        # Work on this
        data = self.__data__

        # If we want specific users
        if users:
            users = [users] if not (isinstance(users, list) or isinstance(users, set)) else users
            data = data.loc[data.id.isin(users)]

        # If we want specific day types (week, weekend)
        if day_types:
            day_types = [day_types] if not isinstance(day_types, list) else day_types

            if 'startDOTW' not in self.__data__.columns:
                self.add_date_type()

            # ... and filter
            data = data.loc[data.startDOTW.isin(day_types)]

        # If we want specific times fo day (morning, noon, etc.)
        if time_of_day:
            time_of_day = [time_of_day] if not isinstance(time_of_day, list) else time_of_day

            if 'startTOD' not in self.__data__.columns:
                self.add_time_of_day()

            # ... and filter
            data = data.loc[data.startTOD.isin(time_of_day)]

        if inplace:
            self.__data__ = data
            return self
        else:
            return data

    @hlp.time_it
    def sync(self, ae: Appevents, inplace=True):
        """
        Restrict timestamps to date ranges as they occur in the Appevents index
        :param ae: Appevents object
        :param inplace: return new data frame or manipulate object data frame
        :return: data frame or None, depending on `inplace`
        """

        # Get dates from Appevents
        dates = ae.get_dates()

        # First filter on users (some may have dropped out due to our criteria)
        users = ae.get_users()
        self.filter(users=users, inplace=True)

        # Get first and last date (per id)
        firsts = dates.apply(min)
        lasts = dates.apply(max)

        # Count for logging
        before = len(self.__data__)

        # Helper function: take df and filter 'time_col' on (start, stop) range
        def filter_timestamps(df: pd.DataFrame, start: pd.Timestamp, stop: pd.Timestamp,
                              time_col='startTime') -> pd.DataFrame:

            # Define filter criterion (edges included)
            criterion = (start <= df[time_col].dt.date) & (df[time_col].dt.date <= stop)

            # Filter the df and return it
            df = df.loc[criterion]
            return df

        # Apply to object
        tqdm.pandas(desc="Syncing Sessions to Appevents")
        result = self.__data__.groupby('id').progress_apply(lambda df: filter_timestamps(df,
                                                                                         start=firsts[df.id.iloc[0]],
                                                                                         stop=lasts[df.id.iloc[
                                                                                             0]])).reset_index(
            drop=True)

        # Count for logging
        after = len(result)

        log(f'Synced Sessions with Appevents input: went from {before} to'
            f' {after} lines ({round(100 * (before - after) / before, 2)}% less).')

        if inplace:
            self.__data__ = result
        else:
            return result

    # Getters #
    ###########

    def get_data(self) -> pd.DataFrame:
        """
        Return sessions data frame
        """
        return self.__data__

    def get_users(self) -> list:
        """
        Returns a list of unique users
        """
        return list(self.__data__ .id.unique())

    def get_days(self) -> pd.Series:
        """
        Returns the number of unique days
        """
        return self.__data__ .groupby('id').startDate.nunique().rename('days')

    def get_sessions(self) -> pd.Series:
        """
        Returns the number of sessions
        """
        return self.__data__.groupby('id')['startTime'].count().rename('sessions')

    def get_durations(self) -> pd.Series:
        """
        Returns the total duration
        """
        return self.__data__.groupby('id').duration.sum().rename('durations')

    # Compound getters #
    ####################

    def get_daily_sessions(self, avg=False) -> pd.Series:
        """
        Returns average number of sessions per day
        """

        # Field name
        name = 'avg_daily_sessions'

        if avg:
            return self.__data__.groupby(['id', 'startDate'])['startTime'].count().reset_index(). \
                    groupby('id')['startTime'].mean().rename(name)
        else:
            return self.__data__.groupby(['id', 'startDate'])['startTime'].count().rename(name)


    def get_daily_durations(self) -> pd.Series:
        """
        Returns duration per day
        """

        # Field name
        name = 'daily_durations'

        return self.__data__.groupby(['id', 'startDate']).duration.sum().reset_index(). \
            groupby('id').duration.mean().rename(name)

    def get_daily_sessions_sd(self) -> pd.Series:
        """
        Returns standard deviation on number of sessions per day
        """

        # Field name
        name = 'daily_events_sd'

        return self.__data__.groupby(['id', 'startDate'])['startTime'].count().reset_index(). \
            groupby('id')['startTime'].std().rename(name)

    def get_daily_durations_sd(self) -> pd.Series:
        """
        Returns duration per day
        """

        # Field name
        name = 'daily_durations_sd'

        return self.__data__.groupby(['id', 'startDate']).duration.sum().reset_index(). \
            groupby('id').duration.std().rename(name)


if __name__ == "__main__":
    ###########
    # EXAMPLE #
    ###########

    hlp.hi()
    hlp.set_param(log_level=1)

    data = hlp.load(path='../../data/assume/lfael_sessions.csv',
                    index='sessions', sep=';')
    ae = Appevents.load_data(path='../../data/assume/lfael_appevents.csv', sep=';')

    se = Sessions(data=data)
    se.sync(ae)

    '''hlp.format_data(df=data, index='sessions')

    se = Sessions(data=data)

    se2 = Sessions.load_data(path="../../data/glance/sessions/0a0fe3ed-d788-4427-8820-8b7b696a6033_sessions.parquet",
                             sep=";")

    se3 = se2.merge(data)

    print(se3.get_days(),
          se3.get_daily_sessions_sd())'''
