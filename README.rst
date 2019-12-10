.. -*- mode: rst -*-

.. figure::  https://github.ugent.be/raw/imec-mict-UGent/mobiledna_py/master/docs/pictures/logo_mobiledna.png?token=AAABYY2K5VSAUAYEQP3BHPS57DRFU
   :align:   center



**mobileDNA** is an open-source statistical package written in Python 3. It can be used in combination with log stemming from the mobileDNA platform. The package contains the following modules:

1. communication

2. basic

3. advanced

4. dashboards



The package is intended for users who like to get hands-on with their data analysis. It can be used and expanded on at will.


Chat
====

If you have questions, please address `Wouter Durnez <Wouter.Durnez@UGent.be>`_ or `Kyle Van Gaeveren <Kyle.VanGaeveren@UGent.be>`_.


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

mobileDNA is a Python 3 package and is currently tested for Python 3.6 and 3.7. mobileDNA is not expected to work with Python 2.7 and below.

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

1. elastic.py
#############

.. warning:: Don't touch this module if you don't have access to the ES server!

.. code-block:: python

  connect(server=cfg.server, port=cfg.port) -> Elasticsearch

Connects to the ES server and return an ES object. Make sure you have the correct version of the :code:`elasticsearch` package installed. This functionality breaks with updates beyond the recommended version.

.. currentmodule:: mobiledna.communication.elastic
.. autofunction:: connect




Development
===========


Contributors
------------

- Nicolas Legrand
- `Richard Höchenberger <http://hoechenberger.net/>`_
- `Arthur Paulino <https://github.com/arthurpaulino>`_
