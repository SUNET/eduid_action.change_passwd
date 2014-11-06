
import json

from datetime import datetime
from bson import ObjectId

import vccs_client

import logging
log = logging.getLogger(__name__)


class TestVCCSClient(object):
    '''
    Mock VCCS client for testing. It stores credentials locally,
    and it only checks for the credential_id to authenticate/revoke.

    It is used as a singleton, so we can manipulate it in the tests
    before the real functions (check_password, add_credentials) use it.
    '''
    def __init__(self):
        self.credentials = {}
        
    def authenticate(self, user_id, factors):
        stored = self.credentials[user_id]
        for factor in factors:
            fdict = factor.to_dict()
            found = False
            for sfactor in stored:
                sdict = sfactor.to_dict()
                if fdict['credential_id'] == sdict['credential_id']:
                    found = True
                    break
            if not found:
                return False
        return True

    def add_credentials(self, user_id, factors):
        self.credentials[user_id] = factors

    def revoke_credentials(self, user_id, revoked):
        stored = self.credentials[user_id]
        for rfactor in revoked:
            rdict = rfactor.to_dict()
            for factor in stored:
                fdict = factor.to_dict()
                if rdict['credential_id'] == fdict['credential_id']:
                    stored.remove(factor)
                    break

test_vccs = TestVCCSClient()


def get_vccs_client(vccs_url):
    """
    Instantiate a VCCS client.

    :param vccs_url: VCCS authentication backend URL
    :type vccs_url: string
    :return: vccs client
    :rtype: VCCSClient
    """
    if vccs_url == 'dummy':
        return test_vccs
    return vccs_client.VCCSClient(
        base_url=vccs_url,
    )


def check_password(vccs_url, password, user, vccs=None):
    """ Try to validate a user provided password.

    Returns False or a dict with data about the credential that validated.

    :param vccs_url: URL to VCCS authentication backend
    :param password: plaintext password
    :param user: user dict
    :param vccs: optional vccs client instance

    :type vccs_url: string
    :type password: string
    :type user: dict
    :type vccs: None or VCCSClient
    :rtype: bool or dict
    """
    passwords = user.get_passwords()
    for password_dict in passwords:
        password_id = password_dict['id']
        if vccs is None:
            vccs = get_vccs_client(vccs_url)
        factor = vccs_client.VCCSPasswordFactor(
            password,
            credential_id=str(password_id),
            salt=password_dict['salt'],
        )
        # Old credentials were created using the username (user['mail']) of the user
        # instead of the user['_id']. Try both during a transition period.
        user_ids = [str(user.get_id()), user.get_mail()]
        if password_dict.get('user_id_hint') is not None:
            user_ids.insert(0, password_dict.get('user_id_hint'))
        try:
            for user_id in user_ids:
                if vccs.authenticate(user_id, [factor]):
                    password_dict['user_id_hint'] = user_id
                    return password_dict
        except Exception:
            pass
    return False


def add_credentials(vccs_url, old_password, new_password, user):
    """
    Add a new password to a user. Revokes the old one, if one is given.

    Returns True on success.

    :param vccs_url: URL to VCCS authentication backend
    :param old_password: plaintext current password
    :param new_password: plaintext new password
    :param user: user object

    :type vccs_url: string
    :type old_password: string
    :type user: User
    :rtype: bool
    """
    password_id = ObjectId()
    vccs = get_vccs_client(vccs_url)
    new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                credential_id=str(password_id))

    passwords = user.get_passwords()
    old_factor = None
    if passwords and old_password:
        # Find the old credential to revoke
        old_password = check_password(vccs_url, old_password, user, vccs=vccs)
        if not old_password:
            return False
        old_factor = vccs_client.VCCSRevokeFactor(
            str(old_password['id']),
            'changing password',
            reference='dashboard',
        )

    if not vccs.add_credentials(str(user.get_id()), [new_factor]):
        log.warning("Failed adding password credential {!r} for user {!r}".format(
            new_factor.credential_id, user.get_id()))
        return False  # something failed
    log.debug("Added password credential {!s} for user {!s}".format(
        new_factor.credential_id, user.get_id()))

    if old_factor:
        # Use the user_id_hint inserted by check_password() until we know all
        # credentials use str(user['_id']) as user_id.
        vccs.revoke_credentials(old_password['user_id_hint'], [old_factor])
        passwords.remove(old_password)
        log.debug("Revoked old credential {!s} (user {!s})".format(
            old_factor.credential_id, user.get_id()))
    elif not old_password:
        # TODO: Revoke all current credentials on password reset for now
        revoked = []
        for password in passwords:
            revoked.append(vccs_client.VCCSRevokeFactor(str(password['id']), 'reset password', reference='dashboard'))
            log.debug("Revoked old credential (password reset) {!s} (user {!s})".format(
                password['id'], user.get_id()))
        if revoked:
            vccs.revoke_credentials(str(user.get_id()), revoked)
        del passwords[:]

    passwords.append({
        'id': password_id,
        'salt': new_factor.salt,
        'source': 'dashboard',
        'created_ts': datetime.now(),
    })
    user.set_passwords(passwords)

    return True


def change_password(request, user, old_password, new_password):
    """ Change the user password, deleting old credentials """
    vccs_url = request.registry.settings.get('vccs_url')
    added = add_credentials(vccs_url, old_password, new_password, user)
    if added:
        user.save(request)
    return added


def provision_credentials(vccs_url, new_password, user):
    """
    This function should be used by tests only
    Provision new password to a user.

    Returns True on success.

    :param vccs_url: URL to VCCS authentication backend
    :param old_password: plaintext current password
    :param new_password: plaintext new password
    :param user: user object

    :type vccs_url: string
    :type old_password: string
    :type user: User
    :rtype: bool
    """
    password_id = ObjectId()
    vccs = get_vccs_client(vccs_url)
    new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                credential_id=str(password_id))

    passwords = user.get_passwords()

    if not vccs.add_credentials(str(user.get_id()), [new_factor]):
        return False  # something failed

    passwords.append({
        'id': password_id,
        'salt': new_factor.salt,
    })
    user.set_passwords(passwords)

    return True
