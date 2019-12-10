# mobiledna_py
Codebase in support of mobileDNA platform. The package consists of the following subpackages:

1.    **communication** - data collection and communication with server
2.    **basics**
  * *help* - functions to make life easier
  * *annotation* (under construction) - functions to enrich your data, by adding annotations such as location metadata or app classification labels
  * *basic* - a first order of metrics, based on simple data aggregation (means and counts) 
3.    **advanced** - second order of metrics, based on more advanced data-analytical methods
4.    **dashboards** - standard line of interactive dashboards

## Communication module

This module should only be used by people who have been given proper access to the data. It contains functions to communicate
with the ES server. It cannot work without a proper config file (so don't even try).

### Connect

`connect` 


Establish connection with data.

```
:param server: server address
:param port: port to go through

:return: Elasticsearch object
```

