#
# Copyright (c) 2015 NORDUnet A/S
# All rights reserved.
#
#   Redistribution and use in source and binary forms, with or
#   without modification, are permitted provided that the following
#   conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#     3. Neither the name of the NORDUnet nor the names of its
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

__author__ = 'eperez'

from pwgen import pwgen

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.exceptions import ConfigurationError

from jinja2 import Environment, PackageLoader

from eduid_am.config import read_setting_from_env
from eduid_am.tasks import update_attributes_keep_result
from eduid_userdb import UserDB
from eduid_userdb.actions.chpass import ChpassUserDB
from eduid_userdb.passwords import Password

from eduid_actions.action_abc import ActionPlugin
from eduid_action.change_passwd.vccs import check_password, add_credentials

import logging
log = logging.getLogger(__name__)


PACKAGE_NAME = 'eduid_action.change_passwd'


env = Environment(loader=PackageLoader(PACKAGE_NAME, 'templates'))


def generate_password(length=12):
    return pwgen(int(length), no_capitalize=True, no_symbols=True)


def generate_suggested_password(request):
    """
    The suggested password is saved in session to avoid form hijacking
    """
    password_length = request.registry.settings.get('password_length', 12)
    if request.method == 'GET':
        password = generate_password(length=password_length)
        password = ' '.join([password[i*4: i*4+4]
                             for i in range(0, len(password)/4)])
        request.session['last_generated_password'] = password
    elif request.method == 'POST':
        password = request.session.get('last_generated_password',
                                       generate_password(
                                           length=password_length))
    return password


class ChangePasswdPlugin(ActionPlugin):

    steps = 1
    translations = {}

    @classmethod
    def get_translations(cls):
        return cls.translations

    @classmethod
    def includeme(self, config):
        '''
        Plugin specific configuration
        '''
        settings = config.registry.settings

        for item in ('mongo_uri',
                     'vccs_url'):
            settings[item] = read_setting_from_env(settings, item, None)
            if settings[item] is None:
                raise ConfigurationError(
                    'The {0} configuration option is required'.format(item))

        for item, default in (
                ('password_length', 12),
                ('password_entropy', 60)):
            settings[item] = int(read_setting_from_env(settings,
                                                       item, default))

        chpasswd_db = ChpassUserDB(settings['mongo_uri'])
        settings['chpasswd_db'] = chpasswd_db
        config.set_request_property(
            lambda x: x.registry.settings['chpasswd_db'],
            'chpasswd_db',
            reify=True)

    def get_number_of_steps(self):
        return self.steps

    def get_action_body_for_step(self, step_number, action,
                                 request, errors=None):
        if errors is None:
            errors = {}
        template = env.get_template('main.jinja2')
        context = {
            '_': self.get_ugettext(request),
            'csrf_token': request.session.get_csrf_token(),
            'suggested_password': generate_suggested_password(request),
            'password_entropy': request.registry.settings.get(
                'password_entropy'),
            'errors': errors,
            }
        return template.render(**context)

    def perform_action(self, action, request):
        _ = self.get_ugettext(request)
        self._check_csrf_token(request)
        old_password = request.POST.get('old_password', '')
        old_password = old_password.replace(" ", "")
        userid = action['user_oid']
        user = request.userdb.get_user_by_oid(userid)
        self._check_old_password(request, user, old_password)
        added = self._change_password(request, user, old_password)

        if not added:
            message = _('An error has occured while updating your password, '
                        'please try again or contact support '
                        'if the problem persists.')
            raise self.ActionError(message)

        request.chpasswd_db.save(user)
        logger.debug("Asking for sync of {!s} by Attribute Manager".format(user))
        rtask = update_attributes_keep_result.delay('chpasswd', str(user.user_id))
        try:
            result = rtask.get(timeout=10)
            logger.debug("Attribute Manager sync result: {!r}".format(result))
        except Exception, e:
            logger.exception("Failed Attribute Manager sync request: " + str(e))
            message = _('There were problems with your submission. '
                        'You may want to try again later, '
                        'or contact the site administrators.')
            request.session.flash(message)
            raise HTTPInternalServerError()


    #  Helper methods
    def _check_csrf_token(self, request):
        value = request.POST.get('csrf', '')
        token = request.session.get_csrf_token()
        if value != token:
            log.debug("CSRF token validation failed: "
                      "Form {!r} != Session {!r}".format(value, token))
            _ = self.get_ugettext(request)
            err = _("Invalid CSRF token")
            raise HTTPBadRequest(err)

    def _check_old_password(self, request, user, old_password):
        # Load user from database to ensure we are working
        # on an up-to-date set of credentials.
        vccs_url = request.registry.settings.get('vccs_url')
        password = check_password(vccs_url, old_password, user)
        if not password:
            _ = self.get_ugettext(request)
            errors = {'old_password': _('Current password is incorrect')}
            raise self.ValidationError(errors)

    def _change_password(self, request, user, old_password):

        if request.POST.get('use_custom_password') == 'true':
            # The user has entered his own password and it was verified by
            # validators
            log.debug("Password change for user {!r} "
                      "(custom password).".format(user.user_id))
            new_password = request.POST.get('custom_password')

        else:
            # If the user has selected the suggested password, then it should
            # be in session
            log.debug("Password change for user {!r} "
                      "(suggested password).".format(user.user_id))
            new_password = generate_suggested_password(request)

        new_password = new_password.replace(' ', '')
        vccs_url = request.registry.settings.get('vccs_url')
        added = add_credentials(vccs_url, old_password, new_password, user)
        return added
