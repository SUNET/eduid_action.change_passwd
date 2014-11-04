.. contents::

Introduction
============

Change password for eduid-actions.


Install
-------

Install with pip or easy_install in a python environment
where the eduid-actions app is deployed.

Configure
---------

in the ini configuration of the eduid-actions app, add a setting

Test
----

Once installed with eduid-actions, test it with::

  $ cd eduid_action.change_passwd/src/
  $ source /path/to/eduid-actions/bin/activate
  $ python /path/to/eduid-actions/eduid_actions/setup.py nosetests
