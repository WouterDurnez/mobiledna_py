# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

APPEVENTS CLASS

-- Coded by Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

from collections import Counter

import pandas as pd
from tqdm import tqdm

import mobiledna.basics.help as hlp
from mobiledna.basics.annotate import add_category
from mobiledna.basics.help import log

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Appevents:

    def __init__(self, data: pd.DataFrame = None, add_categories=False, get_session_sequences=False):

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

        # Downcast battery column
        data.battery = data.battery.astype('uint8')

        # Factorize ids
        # data.id = data.id.astype('category')

        # Factorize apps
        # data.application = data.application.astype('category')

        # Factorize sessions
        # data.session = data.session.astype('category')

        # Sort data frame
        data.sort_values(by=['id', 'startTime'], inplace=True)

        # Set data attribute
        self.__data__ = data

        # Add date columns
        self.__data__ = hlp.add_dates(df=self.__data__, index='appevents')

        # Add duration columns
        self.__data__ = hlp.add_duration(df=self.__data__)

        # Add categories
        if add_categories:
            self.add_category()

        # Initialize attributes
        self.__session_sequences__ = self.get_session_sequences() if get_session_sequences else None

    @classmethod
    def load(cls, path: str, file_type='infer', sep=',', decimal='.'):
        """
        Construct Appevents object from path

        :param path: path to the file
        :param file_type: file extension (csv, parquet, or pickle)
        :param sep: separator for csv files
        :param decimal: decimal for csv files
        :return: Appevents object
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

    def filter(self, category=None, application=None):

        # If we want category-specific info, make sure we have category column
        if category:
            categories = [category] if not isinstance(category, list) else category

            if 'category' not in self.__data__.columns:
                self.add_category()

            # ... and filter
            data = self.__data__.loc[self.__data__.category.isin(categories)]

        # If we want application-level info
        elif application:
            applications = [application] if not isinstance(application, list) else application

            # ... filter
            data = self.__data__.loc[self.__data__.application.isin(applications)]

        else:
            data = self.__data__

        return data

    def merge(self, *appevents: pd.DataFrame):
        """
        Merge new data into existing Appevents object.

        :param appevents: data frame with appevents
        :return: new Appevents object
        """

        new_data = pd.concat([self.__data__, *appevents], sort=False)

        return Appevents(data=new_data)

    def add_category(self, scrape=False, overwrite=False):

        self.__data__ = add_category(df=self.__data__, scrape=scrape, overwrite=overwrite)

    # Getters #
    ###########

    def get_users(self) -> list:
        """
        Returns a list of unique users
        """
        return list(self.__data__.id.unique())

    def get_applications(self) -> dict:
        """
        Returns an {app: app count} dictionary
        """

        return Counter(list(self.__data__.application))

    def get_days(self) -> pd.Series:
        """
        Returns the number of unique days
        """
        return self.__data__.groupby('id').startDate.nunique().rename('days')

    def get_events(self) -> pd.Series:
        """
        Returns the number of appevents
        """

        return self.__data__.groupby('id').application.count().rename('events')

    def get_durations(self) -> pd.Series:
        """
        Returns the total duration
        """
        return self.__data__.groupby('id').duration.sum().rename('durations')

    def get_session_sequences(self) -> list:
        """
        Returns a list of all session sequences
        """

        sessions = []

        t_sessions = tqdm(self.__data__.session.unique())
        t_sessions.set_description('Extracting sessions')

        for session in t_sessions:
            sessions.append(tuple(self.__data__.loc[self.__data__.session == session].application))

        return sessions

    # Compound getters #
    ####################

    def get_daily_events(self, category=None, application=None) -> pd.Series:
        """
        Returns number of appevents per day
        """

        # Field name
        name = ('daily_events' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '')).lower()

        # Filter data on request
        data = self.filter(category=category, application=application)

        return data.groupby(['id', 'startDate']).application.count().reset_index(). \
            groupby('id').application.mean().rename(name)

    def get_daily_durations(self, category=None, application=None) -> pd.Series:
        """
        Returns duration per day
        """

        # Field name
        name = ('daily_durations' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '')).lower()

        # Filter data on request
        data = self.filter(category=category, application=application)

        return data.groupby(['id', 'startDate']).duration.sum().reset_index(). \
            groupby('id').duration.mean().rename(name)

    def get_daily_events_sd(self, category=None, application=None) -> pd.Series:
        """
        Returns standard deviation on number of events per day
        """

        # Field name
        name = ('daily_events_sd' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '')).lower()

        # Filter __data__ on request
        data = self.filter(category=category, application=application)

        return data.groupby(['id', 'startDate']).application.count().reset_index(). \
            groupby('id').application.std().rename(name)

    def get_daily_durations_sd(self, category=None, application=None) -> pd.Series:
        """
        Returns duration per day
        """

        # Field name
        name = ('daily_durations_sd' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '')).lower()

        # Filter __data__ on request
        data = self.filter(category=category, application=application)

        return data.groupby(['id', 'startDate']).duration.sum().reset_index(). \
            groupby('id').duration.std().rename(name)

    def get_sessions_starting_with(self, category=None, application=None, normalize=False):

        # Field name
        name = ('sessions_starting_with' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '')).lower()

        if category:
            categories = [category] if not isinstance(category, list) else category

            return (self.__data__.groupby(['id', 'session']).category.first().isin(categories)). \
                groupby('id').value_counts(normalize=normalize).rename(name)

        if application:
            applications = [application] if not isinstance(application, list) else application

            return (self.__data__.groupby(['id', 'session']).application.first().isin(applications)). \
                groupby('id').value_counts(normalize=normalize).rename(name)


if __name__ == "__main__":
    ###########
    # EXAMPLE #
    ###########

    hlp.hi()
    hlp.set_param(log_level=1)

    # Read sample data
    data = pd.read_parquet(path='../../data/glance/appevents/0a0fe3ed-d788-4427-8820-8b7b696a6033_appevents.parquet')

    # Data path
    data_path = '../../data/glance/appevents/0a0fe3ed-d788-4427-8820-8b7b696a6033_appevents.parquet'

    # More sample data
    data2 = pd.read_parquet(path='../../data/glance/appevents/0a9edba1-14e3-466a-8d0c-f8a8170cefc8_appevents.parquet')
    data3 = pd.read_parquet(path='../../data/glance/appevents/0a48d1e8-ead2-404a-a5a2-6b05371200b1_appevents.parquet')
    data4 = pd.concat([data, data2, data3])

    # Initialize object by loading from path
    print(1)
    ae = Appevents.load(path=data_path)

    # Initialize object and add categories
    print(2)
    ae2 = Appevents(data2, add_categories=True)

    # Initialize object by adding more data (in this case data2 and data3)
    print(3)
    ae3 = ae.merge(data2, data3)
