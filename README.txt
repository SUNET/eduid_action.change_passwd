.. contents::

Introduction
============

Change password plugin for eduid-actions.


Install
-------

Install with pip or easy_install in the python environment where the
eduid-actions app is deployed.

Additionally, install it in the same way in the python environment where the
attribute manager app (eduid-am) is deployed.


Configure
---------

There are 4 settings that can be set in the ini configuration file of the
eduid-actions app that affect this plugin.

mongo_uri
  URI of the mongoDB service.

vccs_url
  URL of the VCCS service.

password_length
  The length of the generated suggested password.

password_entropy
  The minimum entropy required for custom passwords provided by the users.

Usage
-----

To use this plugin, it is necessary to add actions to the actions DB with the
`action` field set to `change_passwd`. An example action doc might be::

  {
    '_id': ObjectId('234567890123456789012300'),
    'user_oid': ObjectId('124567890123456789012311'),
    'action': 'change_passwd',
    'preference': 100,
  }

This will cause the IdP to stop the login process when the logging in user
has an id that matches the `user_oid` in the action. The user will then be
directed to a form to change her password, and after doing that (if there
are no more pending actions) the login process will complete.

Test
----

Create a virtualenv, install the package and its testing dependencies, and run
`nosetests`.


  $ cd eduid_action.change_passwd
  $ virtualenv venv
  $ source venv/bin/activate
  $ python setup.py testing
  $ nosetests
