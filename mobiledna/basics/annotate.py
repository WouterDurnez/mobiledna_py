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
from bs4 import BeautifulSoup
from requests import get
from tqdm import tqdm

from mobiledna.basics import help as hlp
from mobiledna.basics.help import log


def scrape_play_store(app_names: list, cache=None, force=False) -> (dict, list):
    """
    Scrape app meta data from Google play store.

    :param app_name: the official app name (e.g., com.facebook.katana)
    :return: dict with meta data for apps that got a hit, list with remaining apps
    """

    try:
        cache = np.load(file=join(hlp.CACHE_DIR, 'app_meta.npy'), allow_pickle=True).item()
    except:
        log('No cache was found for app meta data.', lvl=3)

    # Play store URL prefix
    play_store_url = 'https://play.google.com/store/apps/details?id='

    # Initialize dict of knowns and list of unknowns
    known_apps = {}
    unknown_apps = []
    cached_apps = 0

    # Loop over app names
    for app_name in tqdm(app_names):

        # Check with local cache, which must be a dict
        if isinstance(cache, dict):

            # Is the app name in the cache's keys?
            if app_name in cache.keys():

                log(f"Info for f{app_name} is in cache.", lvl=3)
                cached_apps += 1

                # If we don't want to overwrite, skip this one
                if not force:
                    continue

        # Combined into full URLs per app
        url = f'{play_store_url}{app_name}'

        # Get HTML from URL
        response = get(url)

        # Create BeautifulSoup object
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get attributes
        try:

            # Store all meta data for this app here
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
            log(f'Got it! <{app_name}> meta data was scraped.', lvl=3)
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

    if isinstance(cache, dict):
        known_apps = {**cache, **known_apps}

    return known_apps, unknown_apps


if __name__ == '__main__':

    # Let's go
    hlp.hi()
    hlp.set_dir(join(pardir, pardir, 'caches'))
    hlp.set_param(log_level=1,
                  data_dir=join(pardir, pardir, 'data', 'glance', 'processed_appevents'),
                  cache_dir=join(pardir, pardir, 'caches'))

    # Load the data and gather apps
    log('Collecting app names.', lvl=1)
    appevents_files = listdir(hlp.DATA_DIR)
    apps = {}

    for appevents_file in tqdm(appevents_files):
        # Load data
        data = hlp.load(path=join(hlp.DATA_DIR, appevents_file), index='appevents')

        # Add apps to the set (no duplicates)
        app_counts = Counter(list(data.application))
        apps = {**apps, **app_counts}

    # Sort apps by number of times they occurred in data
    apps = {k: v for k, v in sorted(apps.items(), key=lambda item: item[1], reverse=True)}

    # Scrape the play store and separate known apps from unknown apps
    log('Scraping from Play Store.', lvl=1)
    app_names = list(apps.keys())
    knowns_play, unknowns_play = scrape_play_store(app_names=app_names)

    # Save meta data to cache folder
    np.save(file=join(hlp.CACHE_DIR, 'app_meta.npy'), arr=knowns_play)

    known_app_names = list(knowns_play.keys())
    unknown_app_names = unknowns_play

    known_app_counts = {k: v for k, v in apps.items() if k in known_app_names}
    unknown_app_counts = {k: v for k, v in apps.items() if k in unknown_app_names}

    # Go through bing
    """bing_url_prefix = 'https://www.bing.com/search?q=site%3Ahttps%3A%2F%2Fapkpure.com+'

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
                     a['href'].__contains__('/versions') or
                     a['href'].__contains__('/download') or
                     a['href'].__contains__('/nl/'))):
                links.add(a['href'])

        if links and len(links) > 1:
            print(app_name, len(links), links)"""
