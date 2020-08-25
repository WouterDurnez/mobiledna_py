# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

ANNOTATION FUNCTIONS

-- Coded by Wouter Durnez
-- mailto:Wouter.Durnez@UGent.be
"""

import random as rnd
from collections import Counter
from os import listdir
from os.path import join, pardir

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from requests import get
from tqdm import tqdm

from mobiledna.basics import help as hlp
from mobiledna.basics.help import log


def scrape_play_store(app_names: list, cache=None, overwrite=False) -> (dict, list):
    """
    Scrape app meta __data__ from Google play store.

    :param app_name: the official app name (e.g., com.facebook.katana)
    :return: dict with meta __data__ for apps that got a hit, list with remaining apps
    """

    try:
        cache = np.load(file=join(hlp.CACHE_DIR, 'app_meta.npy'), allow_pickle=True).item()
    except:
        log('No cache was found for app meta __data__.', lvl=3)

    # Play store URL prefix
    play_store_url = 'https://play.google.com/store/apps/details?id='

    # Initialize dict of knowns and list of unknowns
    known_apps = {}
    unknown_apps = []
    cached_apps = 0

    # Loop over app names
    t_app_names = app_names if hlp.LOG_LEVEL > 1 else tqdm(app_names)
    if hlp.LOG_LEVEL == 1:
        t_app_names.set_description('Scraping')
    for app_name in t_app_names:


        # Check with local cache, which must be a dict
        if isinstance(cache, dict):

            # Is the app name in the cache's keys?
            if app_name in cache.keys():

                log(f"Info for f{app_name} is in cache.", lvl=3)
                cached_apps += 1

                # If we don't want to overwrite, skip this one
                if not overwrite:
                    continue

        # Combined into full URLs per app
        url = f'{play_store_url}{app_name}'

        # Get HTML from URL
        response = get(url)

        # Create BeautifulSoup object
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get attributes
        try:

            # Store all meta __data__ for this app here
            meta = {'source': 'play_store'}

            # Find the name
            name = soup.find('h1', {'class': 'AHFaub'})

            # If we can't even find that, get out of here
            if not name:
                raise Exception(f'Could not find anything on {app_name}.')
            else:
                meta['name'] = name.text

            # Find info
            info = soup.find_all(attrs={'class': 'R8zArc'})

            # ... extract text where possible
            info_text = [info_bit.text for info_bit in info]

            # ... and fill in the blanks
            while len(info_text) < 3:
                info_text.append(None)

            meta['company'] = info_text[0]
            meta['genre1'] = info_text[1]
            meta['genre2'] = info_text[2]

            # Find purchase info
            purchases = soup.find('div', {'class': 'bSIuKf'})
            if purchases:
                meta['purchases'] = purchases.text

            # Find rating info
            rating = soup.find('div', {'class': 'BHMmbe'})
            if rating:
                meta['rating'] = rating.text

            # Add it to the big dict (lol)
            log(f'Got it! <{app_name}> meta __data__ was scraped.', lvl=3)
            known_apps[app_name] = meta

        except Exception as e:
            log(f'Problem for <{app_name}> - {e}', lvl=3)
            unknown_apps.append(app_name)

        zzz = rnd.uniform(1, 3)
        # print(f'Sleeping for {round(zzz, 2)} seconds.')
        # print()
        # time.sleep(zzz)

    log(f"Obtained info for {len(known_apps)} apps.", lvl=1)
    log(f"Failed to get info on {len(unknown_apps)} apps.", lvl=1)
    log(f"{cached_apps} apps were already cached.", lvl=1)

    # Merge new info with cache
    if isinstance(cache, dict):
        if overwrite:
            known_apps = {**known_apps, **cache}
        else:
            known_apps = {**cache, **known_apps}

    # Store app meta __data__ cache
    np.save(file=join(pardir, pardir, 'cache', 'app_meta.npy'), arr=known_apps)

    return known_apps, unknown_apps


def add_category(df: pd.DataFrame, scrape=False, overwrite=False) -> pd.DataFrame:
    """
    Take a __data__ frame and annotate rows with category field, based on application name.

    :param df: __data__ frame (appevents or notifications)
    :param scrape: scrape Play Store for new info (set to True if no meta __data__ is found)
    :return: Annotated __data__ frame
    """

    # Load app meta __data__
    try:
        meta = np.load(join(pardir, pardir, 'cache', 'app_meta.npy'), allow_pickle=True).item()
    except Exception as e:
        log('No app meta __data__ found. Scraping Play store.', lvl=1)
        scrape = True

    # Check if __data__ frame has an application field
    if 'application' not in df:
        raise Exception('Cannot find <application> column in __data__ frame!')

    # Scape the Play store if requested
    if scrape:
        applications = list(df.application.unique())

        meta, _ = scrape_play_store(app_names=applications, cache=meta, overwrite=False)

    # Add category field to row
    def adding_category_row(row: pd.Series):

        if row.application in meta.keys():
            return meta[row.application]['genre1'].lower()
        else:
            return 'unknown'

    tqdm.pandas(desc="Adding category")
    df['category'] = df.progress_apply(adding_category_row, axis=1)

    return df


if __name__ == '__main__':

    # Let's go
    hlp.hi()
    hlp.set_dir(join(pardir, pardir, 'cache'))
    hlp.set_param(log_level=1,
                  data_dir=join(pardir, pardir, '__data__', 'glance', 'processed_appevents'),
                  cache_dir=join(pardir, pardir, 'cache'))

    # Load the __data__ and gather apps
    log('Collecting app names.', lvl=1)
    appevents_files = listdir(hlp.DATA_DIR)
    apps = {}

    for appevents_file in tqdm(appevents_files[0:3]):
        # Load __data__
        data = hlp.load(path=join(hlp.DATA_DIR, appevents_file), index='appevents')

        # Add apps to the set (no duplicates)
        app_counts = Counter(list(data.application))
        apps = {**apps, **app_counts}

    # Sort apps by number of times they occurred in __data__
    apps = {k: v for k, v in sorted(apps.items(), key=lambda item: item[1], reverse=True)}

    data2 = add_category(df=data, scrape=True, overwrite=False)

    # Go through bing
    '''bing_url_prefix = 'https://www.bing.com/search?q=site%3Ahttps%3A%2F%2Fapkpure.com+'

    for app_name in unknowns_play:

        bing_url = bing_url_prefix + app_name

        # Get HTML from URL
        response = get(bing_url)

        # Create BeautifulSoup object
        soup = BeautifulSoup(response.text, 'html.parser')

        a_s = soup.find_all('a', href=True)

        links = set()

        for a in a_s:
            if (a['href'].startswith('https://apkpure.com') and
                a['href'].__contains__(app_name) and
                not (a['href'].__contains__('/fr/') or
                     a['href'].__contains__('/id/') or
                     a['href'].__contains__('/in/') or
                     a['href'].__contains__('/es/') or
                     a['href'].__contains__('/versions') or
                     a['href'].__contains__('/download') or
                     a['href'].__contains__('/nl/'))):
                links.add(a['href'])

        if links and len(links) > 1:
            print(app_name, len(links), links)
        '''
