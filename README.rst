.. -*- mode: rst -*-

.. figure:: docs/pictures/logo_mobiledna.png
   :align: center



**mobileDNA** is an open-source statistical package written in Python 3. It can be used to analyze data stemming from the mobileDNA platform. The package contains the following modules:

1. advanced

2. communication

3. core

4. dashboards


The package is intended for users who like to delve into the raw log data that is provided through the mobileDNA logging application. It can be used and expanded on at will. Go bonkers.


Questions, comments, or just need help?
=======================================

If you have questions, please address `Wouter Durnez <Wouter.Durnez@UGent.be>`_, `Simon Perneel <Simon.Perneel@UGent.be>`_ or `Kyle Van Gaeveren <Kyle.VanGaeveren@UGent.be>`_.


Installation
============

Dependencies
------------

The main dependencies are :

  * NumPy
  * Pandas
  * TQDM
  * MatPlotLib
  * ElasticSearch (6.3.X)
  * PyArrow
  * CSV

In addition, some functions may require :

  * Seaborn
  * PPrint

mobileDNA is a Python 3 package and is currently tested for Python 3.6 - 3.8. mobileDNA is not expected to work with Python 2.7 and below.

User installation
-----------------

Pingouin can be easily installed using pip

.. code-block:: shell

  pip3 install mobiledna


New releases are frequent so always make sure that you have the latest version:

.. code-block:: shell

  pip3 install --upgrade mobiledna

Reference
=========

This documentation is under development. Below, you will find more information for each of the package modules.

Communication module
--------------------

**Warning:** Don't touch this module if you don't have access to the ES server!

1. elastic.py
#############

.. code-block:: python

    connect(server=cfg.server, port=cfg.port) -> Elasticsearch

Connects to the ES server and return an ES object. Make sure you have the correct version of the :code:`elasticsearch` package installed. This functionality breaks with updates beyond the recommended version. Requires a **config file** to work. Returns an Elasticsearch object.


.. code-block:: python

    ids_from_file(dir: str, file_name='ids', file_type='csv') -> list

Reads a list of mobileDNA IDs from a CSV file, containing a single column. Returns them as a list.


.. code-block:: python

    ids_from_server(index="appevents",
                    time_range=('2018-01-01T00:00:00.000', '2030-01-01T00:00:00.000')) -> dict:

Extracts IDs from the server that have logged _something_ in the given time range, in the given index. Returns them as a dictionary (keys: IDs, values: doc_counts).

2. snapshot_restore.py
######################

script that automates the process of snapshot creation, recovery and restoring from a snapshot to the dbcopy server.
Requires a **config file** to work.


Basic module
------------


Development
===========


Contributors
------------

- You?
