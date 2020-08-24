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
from os.path import join, pardir

import numpy as np
import pandas as pd
from tqdm import tqdm

import mobiledna.basics.help as hlp
from mobiledna.basics.annotate import add_category
from mobiledna.basics.help import log

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Appevents:

    def __init__(self, data: pd.DataFrame = None, add_categories=False):

        # Meta variables #
        ##################

        self.__users__ = None
        self.__days__ = None
        self.__events__ = None
        self.__durations__ = None
        self.__id_factorization__ = None
        self.__app_factorization__ = None
        self.__model_factorization__ = None
        self.__session_factorization__ = None

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

        # Set data attribute
        self.data = data

        # Add date columns
        self.data = hlp.add_dates(df=self.data, index='appevents')

        # Add duration columns
        self.data = hlp.add_duration(df=self.data)

        # Add categories
        if add_categories:
            self.add_category()

        # Clean the data
        self.clean()

        # Initialize attributes
        self.__users__ = self.get_users()
        self.__days__ = self.get_days()
        self.__events__ = self.get_events()
        self.__durations__ = self.get_durations()

    @classmethod
    def load(cls, path: str, file_type='infer', sep=',', decimal='.'):
        """
        Construct Appevents object from CSV file.

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

            if 'category' not in self.data.columns:
                self.add_category()

            # ... and filter
            data = self.data.loc[self.data.category.isin(categories)]

        # If we want application-level info
        elif application:
            applications = [application] if not isinstance(application, list) else application

            # ... filter
            data = self.data.loc[self.data.application.isin(applications)]

        else:
            data = self.data

        return data

    def merge(self, *appevents: pd.DataFrame):
        """
        Merge new data into existing Appevents object.

        :param appevents: data frame with appevents
        :return: new Appevents object
        """

        new_data = pd.concat([self.data, *appevents], sort=False)

        return Appevents(data=new_data)

    def add_category(self, meta=None, force=False, scrape=False):

        if 'category' not in self.data.columns and not force:
            self.data = add_category(df=self.data, meta=meta, scrape=scrape)
        else:
            pass

    def clean(self):
        """
        Drop unwanted (Unnamed) columns.

        :return: cleaned Appevents (data)
        """

        for col in self.data.columns:

            if col.__contains__('Unnamed'):
                self.data.drop(labels=col, axis=1, inplace=True)

    # Getters #
    ###########

    def get_users(self) -> pd.Series:
        """
        :return: list of users
        """

        return list(self.data.id.unique())

    def get_applications(self) -> dict:
        """
        :return: all applications and their counts (overall)
        """

        app_counts = Counter(list(self.data.application))

        return app_counts

    def get_days(self) -> pd.Series:
        """
        :return: total number of log days per user
        """
        return self.data.groupby('id').startDate.nunique().rename('days')

    def get_events(self) -> pd.Series:
        """
        :return: total appevent count per user
        """

        return self.data.groupby('id').application.count().rename('events')

    def get_durations(self) -> pd.Series:
        """
        :return: total duration per user
        """
        return self.data.groupby('id').duration.sum().rename('durations')

    def get_session_sequences(self) -> list:
        """
        :return: list of session sequences
        """

        sessions = []

        self.data.groupby('id').sort_values(by=['session', 'startTime'])

        for session in tqdm(self.data.session.unique()):
            sessions.append(self.data.loc[self.data.session == session].application.tolist())

        return sessions

    # Compound getters #
    ####################

    def get_daily_events(self, category=None, application=None) -> pd.Series:
        """
        :return: daily events
        """

        # Filter data on request
        data = self.filter(category=category, application=application)

        return data.groupby(['id', 'startDate']).application.count().reset_index(). \
            groupby('id').application.mean().rename('daily_events')

    def get_daily_durations(self, category=None, application=None) -> pd.Series:
        """
        :return: daily durations
        """

        # Filter data on request
        data = self.filter(category=category, application=application)

        return (self.__durations__ / self.__days__).rename('daily_durations')

    def get_daily_events_sd(self, category=None, application=None) -> pd.Series:

        # Filter data on request
        data = self.filter(category=category, application=application)

        return self.data.groupby(['id', 'startDate']).application.count().reset_index(). \
            groupby('id').application.std().rename('daily_events_sd')

    def get_daily_durations_sd(self, category=None, application=None) -> pd.Series:

        # Filter data on request
        data = self.filter(category=category, application=application)

        return self.data.groupby(['id', 'startDate']).duration.sum().reset_index(). \
            groupby('id').duration.std().rename('daily_duration_sd')


if __name__ == "__main__":
    hlp.set_param(log_level=1,
                  cache_dir=join(pardir, pardir, 'caches'))
    app_meta = np.load(join(hlp.CACHE_DIR, 'app_meta.npy'), allow_pickle=True).item()


    data = pd.read_parquet(path='../../data/glance/appevents/0a0fe3ed-d788-4427-8820-8b7b696a6033_appevents.parquet')

    data_path = '../../data/glance/appevents/0a0fe3ed-d788-4427-8820-8b7b696a6033_appevents.parquet'
    data2 = pd.read_parquet(path='../../data/glance/appevents/0a9edba1-14e3-466a-8d0c-f8a8170cefc8_appevents.parquet')
    data3 = pd.read_parquet(path='../../data/glance/appevents/0a48d1e8-ead2-404a-a5a2-6b05371200b1_appevents.parquet')
    data4 = pd.concat([data, data2, data3])
    ae = Appevents.load(path=data_path)
    ae2 = ae.merge(data2)
    ae3 = ae.merge(data2, data3)
