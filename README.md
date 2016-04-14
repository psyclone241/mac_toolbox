mac_toolbox
===========

Mac OSX Toolbox
-----------------------------

A collection of scripts for making life simpler on my OSX box
1. backupstate.py - Gives JSON output describing the state of your configured Time Machine drive

Installation
------------

No installation at this time

Package Contents
----------------

Nothing is installed, at this time this just runs from command line or make

Usage Instructions
------------------

* python backupstate.py
* make backupstate

Input data
----------

Make sure to create a working copy of config.example.ini, named config.ini

Output data
-----------

* json output describing the state of your time machine drive

Requirements
------------

Python 2.7 or greater and the following libs

* ConfigParser
* sys
* plistlib
* json
* os
* subprocess
* traceback

Contributions
-------------

We welcome contributions to this project. Please fork
and send pull requests with your revisions.
