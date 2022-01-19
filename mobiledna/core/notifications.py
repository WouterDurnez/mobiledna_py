# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

NOTIFICATIONS CLASS

-- Coded by Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import pickle
from collections import Counter

import pandas as pd
from tqdm import tqdm

import mobiledna.core.help as hlp
from mobiledna.core.annotate import add_category, add_time_of_day_annotation, add_date_annotation
from mobiledna.core.appevents import Appevents
from mobiledna.core.help import log

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Notifications:

    def __init__(self, data: pd.DataFrame = None, add_categories=False):

        # Set dtypes #
        ##############

        # Set datetimes
        try:
            data.time = data.time.astype('datetime64[ns]')
        except Exception as e:
            print('Could not convert startTime column to datetime format: ', e)

        # Sort data frame
        data.sort_values(by=['id', 'time'], inplace=True)

        # Set data attribute
        self.__data__ = data

        # Add date columns
        self.__data__ = hlp.add_dates(df=self.__data__, index='notifications')

        # Add categories
        if add_categories:
            self.add_category()

    @classmethod
    def load_data(cls, path: str, file_type='infer', sep=',', decimal='.'):
        """
        Construct Appevents object from path to data

        :param path: path to the file
        :param file_type: file extension (csv, parquet, or pickle)
        :param sep: separator for csv files
        :param decimal: decimal for csv files
        :return: Appevents object
        """

        data = hlp.load(path=path, index='notifications', file_type=file_type, sep=sep, dec=decimal)

        return cls(data=data)

    def to_pickle(self, path: str):
        """
        Store an Appevents object to pickle
        :param path: path to file
        :return: None
        """

        # Setting directory
        dir = '/'.join(path.split('/')[:-1])
        hlp.set_dir(dir)

        # Storing pickle
        with open(file=path, mode='wb') as file:
            pickle.dump(self, file, pickle.HIGHEST_PROTOCOL)
        file.close()

    @classmethod
    def from_pickle(cls, path: str):
        """
        Construct an Appevents object from pickle
        :param path: path to file
        :return: Appevents object
        """

        with open(file=path, mode='rb') as file:
            object = pickle.load(file)
        file.close()

        return object

    def save_data(self, dir: str, name: str, csv=False, pickle=False, parquet=True):
        """
        Save data from Appevents object to data frame
        :param dir: directory to save
        :param name: file name
        :param csv: csv format
        :param pickle: pickle format
        :param parquet: parquet format
        :return: None
        """

        hlp.save(df=self.__data__, dir=dir, name=name, csv_file=csv, pickle=pickle, parquet=parquet)

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
                              time_col='time') -> pd.DataFrame:

            # Define filter criterion (edges included)
            criterion = (start <= df[time_col].dt.date) & (df[time_col].dt.date <= stop)

            # Filter the df and return it
            df = df.loc[criterion]
            return df

        # Apply to object
        tqdm.pandas(desc="Syncing Notifications to Appevents")
        result = self.__data__.groupby('id').progress_apply(lambda df: filter_timestamps(df,
                                                                                         start=firsts[df.id.iloc[0]],
                                                                                         stop=lasts[df.id.iloc[
                                                                                             0]])).reset_index(
            drop=True)

        # Count for logging
        after = len(result)

        log(f'Synced Notifications with Appevents input: went from {before} to'
            f' {after} lines ({round(100 * (before - after) / before, 2)}% less).')

        if inplace:
            self.__data__ = result
        else:
            return result

    def filter(self, users=None, category=None, application=None, day_types=None, time_of_day=None, priority=None,
               posted=None, ongoing=None,
               inplace=False):

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

        # If we want to filter on priority levels
        if priority:
            priority = [priority] if not isinstance(priority, list) else priority

            # ... filter
            data = data.loc[data.priority.isin(priority)]

        # If we want to filter on new (False) or ongoing (True) notifications
        if ongoing is not None:
            ongoing = [ongoing] if not isinstance(ongoing, list) else ongoing

            # ... filter
            data = data.loc[data.ongoing.isin(ongoing)]

        # If we want to filter on the posted variable
        if posted:
            # ... filter
            data = data.loc[data.posted == posted]

        if inplace:
            self.__data__ = data
            return self
        else:
            return data

    def merge(self, *notifications: pd.DataFrame):
        """
        Merge new data into existing Notifications object.

        :param notifications: data frame with notifications
        :return: new Notifications object
        """

        new_data = pd.concat([self.__data__, *notifications], sort=False)
        new_data.drop_duplicates(inplace=True)

        return Notifications(data=new_data)

    def add_category(self, scrape=False, overwrite=False):

        self.__data__ = add_category(df=self.__data__, scrape=scrape, overwrite=overwrite)

    def add_date_type(self, date_cols='date', holidays_separate=False):

        self.__data__ = add_date_annotation(df=self.__data__, date_cols=date_cols, holidays_separate=holidays_separate)

        return self

    def add_time_of_day(self, time_col='startTime'):

        self.__data__ = add_time_of_day_annotation(df=self.__data__, time_cols=time_col)

        return self

    # Getters #
    ###########

    def get_data(self) -> pd.DataFrame:
        """
        Return notifications data frame
        """
        return self.__data__

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
        return self.__data__.groupby('id').date.nunique().rename('days')

    def get_notifications(self) -> pd.Series:
        """
        Returns the number of notifications
        """

        return self.__data__.groupby('id').application.count().rename('notifications')

    # Compound getters #
    ####################

    def get_daily_notifications(self, category=None, application=None, time_of_day=None, priority=0, posted=True, ongoing=None, avg=False) -> pd.Series:
        """
        Returns number of notifications per day
        """

        # Field name
        name = ((f'avg_' if avg else '') +
                'daily_notifications' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '') +
                (f'_{time_of_day}' if time_of_day else '')).lower()

        # Filter data on request
        data = self.filter(category=category, application=application, priority=priority, posted=posted, time_of_day=time_of_day, ongoing=ongoing)

        if avg:
            return data.groupby(['id', 'date']).application.count().reset_index(). \
                groupby('id').application.mean().rename(name)
        else:
            return data.groupby(['id', 'date']).application.count().rename(name)

    def get_daily_notifications_sd(self, category=None, application=None, priority=0, posted=True) -> pd.Series:
        """
        Returns standard deviation on number of events per day
        """

        # Field name
        name = ('daily_notifications_sd' +
                (f'_{category}' if category else '') +
                (f'_{application}' if application else '')).lower()

        # Filter __data__ on request
        data = self.filter(category=category, application=application, priority=priority, posted=posted)

        return data.groupby(['id', 'date']).application.count().reset_index(). \
            groupby('id').application.std().rename(name)


if __name__ == "__main__":
    ###########
    # EXAMPLE #
    ###########

    hlp.hi()
    hlp.set_param(log_level=3)

    # data = hlp.load(path='../../data/assume/eryckaert_notifications.csv',
    #                index='notifications',sep=';')
    ae = Appevents.load_data(path='../../data/assume/eryckaert_appevents.csv', sep=';')
    # hlp.format_data(df=data, index='notifications')

    noti = Notifications.load_data(pathdata='../../data/assume/eryckaert_notifications.csv',
                                   sep=';')
    noti.sync(ae=ae)
