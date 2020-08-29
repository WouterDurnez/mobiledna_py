# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

APPEVENTS CLASS

-- Coded by Kyle Van Gaeveren & Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import pandas as pd

import mobiledna.basics.help as hlp
from mobiledna.basics.help import log

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
    def load(cls, path: str, file_type='infer', sep=',', decimal='.'):
        """
        Construct Sessions object from path.

        :param path: path to the file
        :param file_type: file extension (csv, parquet, or pickle)
        :param sep: separator for csv files
        :param decimal: decimal for csv files
        :return: Sessions object
        """

        # Load data frame, depending on file type
        if file_type == 'infer':

            # Get extension
            file_type = path.split('.')[-1]

            # Only allow the following extensions
            if file_type not in ['csv', 'pickle', 'pkl', 'parquet']:
                raise Exception("ERROR: Could not infer file type!")

            log("Recognized file type as <{type}>.".format(type=file_type), lvl=3)

        # CSV
        if file_type == 'csv':
            data = pd.read_csv(filepath_or_buffer=path,
                               # usecols=,
                               sep=sep, decimal=decimal,
                               error_bad_lines=False)

        # Pickle
        elif file_type == 'pickle' or file_type == 'pkl':
            data = pd.read_pickle(path=path)

        # Parquet
        elif file_type == 'parquet':
            data = pd.read_parquet(path=path, engine='auto')

        # Unknown
        else:
            raise Exception("ERROR: You want me to read what now? Invalid file type! ")

        return cls(data=data)

    def merge(self, *sessions: pd.DataFrame):
        """
        Merge new data into existing Appevents object.

        :param sessions: data frame with appevents
        :return: new Sessions object
        """

        new_data = pd.concat([self.__data__ , *sessions], sort=False)

        return Sessions(data=new_data)

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
        return self.__data__ .groupby('id').duration.sum().rename('durations')

    # Compound getters #
    ####################

    def get_daily_sessions(self) -> pd.Series:
        """
        Returns number of sessions per day
        """

        # Field name
        name = 'daily_sessions'

        return self.__data__.groupby(['id', 'startDate'])['startTime'].count().reset_index(). \
            groupby('id')['startTime'].mean().rename(name)

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

    data = hlp.load(path='../../data/glance/sessions/0a9e1d70-fd9e-47a7-a765-d608587f63d7_sessions.parquet',
                    index='sessions')

    se = Sessions(data=data)
    se2 = Sessions.load(path="../../data/glance/sessions/0a0fe3ed-d788-4427-8820-8b7b696a6033_sessions.parquet",
                        sep=";")

    se3 = se2.merge(data)

    print(se3.get_days(),
          se3.get_daily_sessions_sd())
