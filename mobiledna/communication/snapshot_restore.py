# -*- coding: utf-8 -*-

"""
    __  ___      __    _ __     ____  _   _____
   /  |/  /___  / /_  (_) /__  / __ \/ | / /   |
  / /|_/ / __ \/ __ \/ / / _ \/ / / /  |/ / /| |
 / /  / / /_/ / /_/ / / /  __/ /_/ / /|  / ___ |
/_/  /_/\____/_.___/_/_/\___/_____/_/ |_/_/  |_|

ELASTICSEARCH SCRIPT TO TAKE AND RESTORE AN ES SNAPSHOT

A VPN connection with the ES server is required to carry out commands
The Geckodriver needs to be installed on your computer to make Selenium work. Add the file to this
directory or to your PATH
-> See: https://github.com/SeleniumHQ/selenium/blob/trunk/py/docs/source/index.rst

-- Coded by Simon Perneel & Kyle Van Gaeveren
-- mailto:Simon.Perneel@UGent.be
"""

# import libraries
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import requests
import time
import base64
import config as cfg
import datetime as dt

import mobiledna.core.help as hlp


# ----------------------------------
# ElasticSearch interface commands
# ----------------------------------
def es_post_close():
    """
    Closes an index
    https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-close.html
    :return: status code
    """

    try:
        p_close = requests.post(url="http://10.10.160.36:9200/_all/_close")

        if p_close.status_code == 200:
            print(f"Close POST succesful")

    except Exception as e:
        print(f"Close POST not accepted")
        print(e)
        p_close = 500

    return p_close.status_code


def es_post_open():
    """
    Opens a closed index. For data streams, the API opens any closed backing indices
    https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-open-close.html
    :return: status code
    """
    try:
        p_open = requests.post(url="http://10.10.160.36:9200/_all/_open")

        if p_open.status_code == 200:
            print("Open POST succesful")
        else:
            print("Open POST not accepted")

    except Exception as e:
        print("Open POST not accepted")
        print(e)
        p_open = 500

    return p_open.status_code


def es_post_restore(snapshot: str):
    """
    Restores a snapshot of a cluster or specified data streams and indices
    https://www.elastic.co/guide/en/elasticsearch/reference/current/restore-snapshot-api.html
    :param snapshot: snapshot to restore
    :return: status code
    """

    try:
        p_restore = requests.post(
            f"http://10.10.160.36:9200/_snapshot/mobiledna-fs-snapshots/{snapshot}/_restore"
        )

        if p_restore.status_code == 200:
            print("Restore POST accepted")
        else:
            print("Restore POST not accepted")

        return p_restore.status_code

    except Exception as e:
        print("Something went wrong during RESTORE")
        print(e)


def get_snapshot(latest=None):
    """
    Sends a GET request to grab a list of current snapshots and returns it as a DataFrame.
    :param latest: bool to check only the latest snapshot
    :return: DataFrame with snapshot(s)
    """

    r = requests.get(
        url="http://10.10.160.36:9200/_snapshot/mobiledna-fs-snapshots/_all"
    )
    data = r.json()["snapshots"]
    df = pd.DataFrame.from_dict(data)

    if latest:
        data = r.json()["snapshots"][-1]
        df = pd.DataFrame.from_dict(data, orient="index", ).transpose()

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    cols = ["uuid", "snapshot", "state", "start_time", "end_time"]

    return df[cols]


def get_recovery():
    """
    Sends a GET request to check snapshot recovery on dbcopy.
    :return: DataFrame with cluster id, snapshot and stage of recovery.
    """

    r = requests.get("http://10.10.160.36:9200/_recovery?pretty")
    d = r.json()

    ids = []
    snapshots = []
    stages = []
    sizes = []
    files = []

    for s in d["mobiledna"]["shards"]:
        ids.append(s["id"])

        try:
            snapshots.append(s["source"]["snapshot"])
        except KeyError:
            print("No snapshot added")
            snapshots.append(None)

        stages.append(s["stage"])
        sizes.append(s["index"]["size"]["percent"])
        files.append(s["index"]["files"]["percent"])

    df = pd.DataFrame(
        zip(ids, snapshots, stages, sizes, files),
        columns=["id", "snapshot", "stage", "size_pct", "file_pct"],
    )

    return df


# ----------------------------------
# Selenium web browsing functions
# ----------------------------------
def mdna_login(driver, user: str, pw: str):
    """
    Log in to the mobileDNA admin website.
    :param driver: selenium webdriver
    :param user: mobiledna account username
    :param pw: mobiledna account password
    return: webdriver
    """

    driver.get("https://www.mobiledna.be/")

    input_mail = driver.find_element(By.ID, "email")

    input_mail.send_keys(user)

    input_password = driver.find_element(By.ID, "password")

    input_password.send_keys(pw)

    login_button = driver.find_element(By.TAG_NAME, "button")

    login_button.click()

    return driver


def mdna_list_snapshot(driver):
    """
    List current snapshots of mDNA repo and their status
    :param driver: selenium webdriver
    :return: status code
    """
    driver.get("https://www.mobiledna.be/admin/snapshots")

    time.sleep(2)

    snapshot = driver.find_element(By.CLASS_NAME, "well").text
    status = driver.find_element(By.CLASS_NAME, "badge").text

    print(f"{snapshot} - {status}")

    return status


def mdna_create_snapshot(driver):
    """
    Clicks the 'create snapshot button' (automation at its best :))
    :param driver: selenium webdriver
    :return: webdriver
    """

    button_create = driver.find_element(By.CLASS_NAME, "btn-primary")

    button_create.click()

    print(f"Created snapshot, please hold.")

    return driver


def mdna_check_alert(driver, refresh: float = 5):
    """
    Checks whether snapshot creation is completed
    :param driver: selenium webdriver
    :param refresh: minutes to wait before refresh
    :return: "READY"
    """
    status = mdna_list_snapshot(driver=driver)

    while status == "IN_PROGRESS":
        print(
            f"{dt.datetime.now()} - Snapshot creation in progress. Trying again in {refresh} minutes"
        )

        time.sleep(refresh * 60)

        status = mdna_list_snapshot(driver=driver)

        if status == "SUCCESS":
            print(f"{dt.datetime.now()} - Snapshot creation completed!")
            return "READY"

    else:
        print(f"Snapshot is ready!")


def create_new_snapshot_combined(driver=None):
    """
    Log in to mDNA website, creates snapshot and checks completion
    :param driver: selenium webdriver
    :return 'READY'
    """
    if not driver:
        options = Options()
        ser = Service(r'./geckodriver')
        driver = webdriver.Firefox(service=ser, options=options)

    # login
    print("Logging in...")

    user = base64.b64decode(cfg.usr).decode("utf-8")
    pwd = base64.b64decode(cfg.pwd).decode("utf-8")

    mdna_login(driver, user=user, pw=pwd)

    print("Logged in. Browsing to snapshots.")

    # browse snapshots
    driver.get("https://mobiledna.be/admin/snapshots")
    mdna_list_snapshot(driver)

    # create snapshot
    print("Creating new snapshot.")
    driver = mdna_create_snapshot(driver)

    # check completion
    print("Checking completion.")
    status = mdna_check_alert(driver=driver, refresh=0.5)

    # if completed
    # close driver
    if status == "READY":
        print("Snapshot complete!")

        driver.close()

        return "READY"


def check_recovery_status(df: pd.DataFrame):
    """
    Checks whether snapshot has been recovered
    :param df: dataframe with recovery status
    """
    df = df.copy()

    rows = len(
        df[
            (df["stage"] == "DONE")
            & (df["size_pct"] == "100.0%")
            & (df["file_pct"] == "100.0%")
            ]
    )

    return rows


# ----------------------------------
# Restoring snapshot
# ----------------------------------
def restore_snapshot(snapshot: str, sleep: int = 30):
    """
    function combining the different steps of restoring an ES snapshot.
    Takes a snapshot, closes ES, restores snapshot and opens ES again.

    :param snapshot: snapshot (str) you want to restore
    :param sleep: time (in sec) to wait between checks if restore is completed
    :return: no return
    """

    # First, we close the ES indexes
    try:
        close = es_post_close()
        print("Closing ES indexes...")

    except Exception as e:
        print("Something went wrong during CLOSE")
        print(e)
        close = 0

    # If close successful, we start the restore
    if close == 200:
        try:
            restore = es_post_restore(snapshot)
            print(f"Restoring ({restore}) snapshot {snapshot}")

        except Exception as e:
            print("Something went wrong during RESTORE")
            print(e)
            p_open = es_post_open()
            restore = 500

    # If restore is accepted (= 200), we check recovery of clusters (5)
    if restore == 200:
        try:
            time.sleep(5)
            check_count = check_recovery_status(get_recovery())
            print(f"Checking restoration: {check_count} / 5 clusters")

            while check_count != 5:
                print(f"Not all clusters restored. Trying again in {sleep}s")
                time.sleep(30)

                check_count = check_recovery_status(get_recovery())
                print(f"{check_count} / 5 clusters restored ")

                if check_count == 5:
                    print("Snapshot recovery complete!")
                    print("Opening ES indexes...")
                    es_post_open()

                    break

        except Exception as e:
            print("Something went wrong during RECOVERY")
            print(e)


def main():
    hlp.hi('Take and recover a snapshot to dbcopy server')
    hlp.log('A VPN connection is required to connect to ES server')
    # create new snapshot
    create_new_snapshot_combined()
    # pick the snapshot to restore
    snapshot_to_restore = get_snapshot(latest=True)
    # restore snapshot to dbcopy server
    restore_snapshot(snapshot_to_restore["snapshot"][0])
    print('')
    print(f'Backup of snapshot {snapshot_to_restore["snapshot"][0]} completed')


if __name__ == "__main__":
    main()
