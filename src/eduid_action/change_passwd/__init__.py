
from pwgen import pwgen

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.exceptions import ConfigurationError

from jinja2 import Environment, PackageLoader

from eduid_am.db import MongoDB
from eduid_am.userdb import UserDB
from eduid_am.config import read_setting_from_env

from eduid_actions.action_abc import ActionPlugin
from eduid_action.change_passwd.vccs import check_password, change_password

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

        for item in ('mongo_uri_dashboard',
                     'mongo_uri_am',
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

        mongo_replicaset = settings.get('mongo_replicaset', None)
        if mongo_replicaset is not None:
            profiles_mongodb = MongoDB(db_uri=settings['mongo_uri_dashboard'],
                                       replicaSet=mongo_replicaset)
            am_mongodb = MongoDB(db_uri=settings['mongo_uri_am'],
                                 replicaSet=mongo_replicaset)
        else:
            profiles_mongodb = MongoDB(db_uri=settings['mongo_uri_dashboard'])
            am_mongodb = MongoDB(db_uri=settings['mongo_uri_am'])
        profiles_db = profiles_mongodb.get_database()
        settings['profiles_db'] = profiles_db
        config.set_request_property(
            lambda x: x.registry.settings['profiles_db'],
            'profiles_db',
            reify=True)
        am_db = am_mongodb.get_database()
        settings['am_db'] = am_db
        config.set_request_property(
            lambda x: x.registry.settings['am_db'],
            'am_db',
            reify=True)
        userdb = UserDB(settings)
        settings['userdb'] = userdb
        config.set_request_property(
            lambda x: x.registry.settings['userdb'],
            'userdb',
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
                'password_entropy', '60'),
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

        if request.POST.get('use_custom_password') == 'true':
            # The user has entered his own password and it was verified by
            # validators
            log.debug("Password change for user {!r} "
                      "(custom password).".format(userid))
            new_password = request.POST.get('custom_password')

        else:
            # If the user has selected the suggested password, then it should
            # be in session
            log.debug("Password change for user {!r} "
                      "(suggested password).".format(userid))
            new_password = generate_suggested_password(request)

        new_password = new_password.replace(' ', '')

        self.changed = change_password(request, user,
                                       old_password, new_password)
        if not self.changed:
            message = _('An error has occured while updating your password, '
                        'please try again or contact support '
                        'if the problem persists.')
            raise self.ActionError(message)

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
            err = _('Current password is incorrect')
            raise self.ValidationError(err)
