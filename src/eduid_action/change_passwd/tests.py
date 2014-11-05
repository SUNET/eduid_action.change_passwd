# -*- coding: utf8 -*

from datetime import datetime
from bson import ObjectId
from copy import deepcopy
import pymongo
from eduid_am.db import MongoDB
from eduid_actions.testing import FunctionalTestCase


CHPASS_ACTION = {
        '_id': ObjectId('234567890123456789012300'),
        'user_oid': ObjectId('123467890123456789014567'),
        'action': 'change_passwd',
        'preference': 100,
        'params': {
            }
        }

TEST_USER = {
    '_id': ObjectId('123467890123456789014567'),
    'givenName': 'John',
    'sn': 'Smith',
    'displayName': 'John Smith',
    'mail': 'johnsmith@example.com',
    'norEduPersonNIN': ['197801011234'],
    'photo': 'https://pointing.to/your/photo',
    'preferredLanguage': 'en',
    'eduPersonPrincipalName': 'hubba-bubba',
    'modified_ts': datetime.strptime("2013-09-02T10:23:25", "%Y-%m-%dT%H:%M:%S"),
    'eduPersonEntitlement': [
        'urn:mace:eduid.se:role:admin',
        'urn:mace:eduid.se:role:student',
    ],
    'maxReachedLoa': 3,
    'mobile': [{
        'mobile': '+34609609609',
        'verified': True
    }, {
        'mobile': '+34 6096096096',
        'verified': False
    }],
    'mailAliases': [{
        'email': 'johnsmith@example.com',
        'verified': True,
    }, {
        'email': 'johnsmith2@example.com',
        'verified': True,
    }, {
        'email': 'johnsmith3@example.com',
        'verified': False,
    }],
    'passwords': [{
        'id': ObjectId('112345678901234567890123'),
        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
    }],
    'postalAddress': [{
        'type': 'home',
        'country': 'SE',
        'address': "Long street, 48",
        'postalCode': "123456",
        'locality': "Stockholm",
        'verified': True,
    }, {
        'type': 'work',
        'country': 'ES',
        'address': "Calle Ancha, 49",
        'postalCode': "123456",
        'locality': "Punta Umbria",
        'verified': False,
    }],
}


class ChPassActionTests(FunctionalTestCase):

    def setUp(self):
        super(ChPassActionTests, self).setUp()
        settings = self.testapp.app.registry.settings
        mongo_uri_base = 'mongodb://localhost:{0}/'.format(str(self.port))
        mongo_uri_am = mongo_uri_base + 'eduid_am'
        mongo_uri_dashboard = mongo_uri_base + 'eduid_dashboard'
        try:
            mongodb_am = MongoDB(mongo_uri_am)
            mongodb_dashboard = MongoDB(mongo_uri_dashboard)
        except pymongo.errors.ConnectionFailure:
            self.setup_temp_db()
            mongo_uri_base = 'mongodb://localhost:{0}/'.format(str(self.port))
            mongo_uri_am = mongo_uri_base + 'eduid_am'
            mongo_uri_dashboard = mongo_uri_base + 'eduid_dashboard'
            mongodb_am = MongoDB(mongo_uri_am)
            mongodb_dashboard = MongoDB(mongo_uri_dashboard)
        settings.update({
            'mongo_uri_am': mongo_uri_am,
            'mongo_uri_dashboard': mongo_uri_dashboard,
            'vccs_url': 'dummy',
            })
        self.am_db = mongodb_am.get_database()
        self.dashboard_db = mongodb_dashboard.get_database()

    def tearDown(self):
        self.am_db.attributes.drop()
        self.dashboard_db.profiles.drop()
        super(ChPassActionTests, self).tearDown()

    def test_action_success(self):
        self.db.actions.insert(CHPASS_ACTION)
        # token verification is disabled in the setUp
        # method of FunctionalTestCase
        url = ('/?userid=123467890123456789014567'
                '&token=abc&nonce=sdf&ts=1401093117')
        res = self.testapp.get(url)
        self.assertEqual(res.status, '302 Found')
        res = self.testapp.get(res.location)
        self.assertIn('Change password', res.body)
        form = res.forms['passwords-form']
