# -*- coding: utf8 -*

from datetime import datetime
import bson
from copy import deepcopy
from mock import patch
import vccs_client
from eduid_am.db import MongoDB
from eduid_userdb.user import User
from eduid_userdb.testing import MOCKED_USER_STANDARD
from eduid_actions.testing import FunctionalTestCase
from eduid_actions.context import RootFactory
from eduid_common.authn.testing import get_vccs_client


TEST_USER_ID = bson.ObjectId('012345678901234567890123')

TEST_PASSWORD_1 = {
    'id': bson.ObjectId('112345678901234567890123'),
    'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
}


CHPASS_ACTION = {
    '_id': bson.ObjectId('234567890123456789012300'),
    'user_oid': TEST_USER_ID,
    'action': 'change_passwd',
    'preference': 100,
    'params': {
    }
}

class ChPassActionTests(FunctionalTestCase):

    def setUp(self):
        super(ChPassActionTests, self).setUp(settings={'vccs_url': 'dummy'})
        self.chpass_db = self.testapp.app.registry.settings['chpasswd_db']
        user_data = deepcopy(MOCKED_USER_STANDARD)
        user_data['modified_ts'] = datetime.utcnow()
        self.amdb.save(User(data=user_data), check_sync=False)
        self.test_user_id =  '012345678901234567890123'
        self.vccs = get_vccs_client(self.settings['vccs_url'])
        import eduid_common.authn.vccs
        self.vccs_patcher = patch.object(eduid_common.authn.vccs,
                'get_vccs_client', get_vccs_client)
        self.vccs_patcher.start()

    def tearDown(self):
        self.vccs_patcher.stop()
        self.chpass_db._drop_whole_collection()
        self.amdb._drop_whole_collection()
        super(ChPassActionTests, self).tearDown()

    def add_credential(self, userid, passwd):
        factor = vccs_client.VCCSPasswordFactor(
            passwd,
            credential_id=str(TEST_PASSWORD_1['id']),
            salt=str(TEST_PASSWORD_1['salt']),
        )
        self.vccs.add_credentials(str(userid), [factor])

    def get_password_form(self):
        self.actions_db._coll.insert(CHPASS_ACTION)
        self.add_credential(TEST_USER_ID, 'abcd')
        # token verification is disabled in the setUp
        # method of FunctionalTestCase
        url = ('/?userid=' + str(TEST_USER_ID) +
               '&token=abc&nonce=sdf&ts=1401093117')
        res = self.testapp.get(url)
        self.assertEqual(res.status, '302 Found')
        res = self.testapp.get(res.location)
        self.assertIn('Change password', res.body)
        return res.forms['passwords-form']

    def test_action_success(self):
        form = self.get_password_form()
        form['old_password'] = 'abcd'
        self.assertEqual(self.actions_db.db_count(), 1)
        res = form.submit('save')
        self.assertEqual(self.actions_db.db_count(), 0)

    def test_action_wrong_password(self):
        form = self.get_password_form()
        form['old_password'] = 'efgh'
        self.assertEqual(self.actions_db.db_count(), 1)
        res = form.submit('save')
        self.assertIn('Current password is incorrect', res.body)
