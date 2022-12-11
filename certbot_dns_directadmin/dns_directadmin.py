"""DNS Authenticator for DirectAdmin."""
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

from certbot_dns_directadmin.directadmin import DirectAdminClient, DirectAdminClientException

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for DirectAdmin
    This Authenticator uses the DirectAdmin API to fulfill a dns-01 challenge.
    """

    description = ('Obtain certificates using a DNS TXT record (if you are using a DirectAdmin server for '
                   'DNS).')
    ttl = 120

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials: Optional[CredentialsConfiguration] = None

    @classmethod
    def add_parser_arguments(cls, add, **kwargs) -> None:
        super(Authenticator, cls).add_parser_arguments(add,
                                                       default_propagation_seconds=60)
        add("credentials", type=str, help="The DirectAdmin credentials INI file")

    @staticmethod
    def _validate_credentials(credentials: CredentialsConfiguration) -> None:
        url = credentials.conf('url')
        username = credentials.conf('username')
        password = credentials.conf('password')
        token = credentials.conf('token')

        if not url:
            raise errors.PluginError('{}: dns_directadmin_url is required')
        else:
            if not username and (not token or not password):
                raise errors.PluginError('{}: dns_directadmin_username (Username) and  '
                                         'dns_directadmin_password (Password) or dns_directadmin_token (Access Token) '
                                         'are required')
            if username and (not token and not password):
                raise errors.PluginError('{}: dns_directadmin_password (Password) '
                                         'or dns_directadmin_token (Access Token) '
                                         'are required')

    def more_info(self):  # pylint: disable=missing-docstring
        return self.description

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            'credentials',
            'DirectAdmin credentials INI file',
            None,
            self._validate_credentials
        )

    def _perform(self, domain, validation_domain_name, validation):
        self._get_directadmin_client().add_txt_record(validation_domain_name, validation)

    def _cleanup(self, domain, validation_domain_name, validation):
        self._get_directadmin_client().del_txt_record(validation_domain_name, validation)

    def _get_directadmin_client(self) -> "_DirectadminClient":
        if not self.credentials:  # pragma: no cover
            raise errors.Error("Plugin has not been prepared.")
        if self.credentials.conf('url'):  # pragma: no cover
            if self.credentials.conf('password') and not self.credentials.conf('token'):
                return _DirectadminClient(self.credentials.conf('url'),
                                          self.credentials.conf('username'),
                                          self.credentials.conf('password'))
            elif not self.credentials.conf('password') and self.credentials.conf('token'):
                return _DirectadminClient(self.credentials.conf('url'),
                                          self.credentials.conf('username'),
                                          self.credentials.conf('token'))


class _DirectadminClient:
    """Encapsulate communications with the directadmin API"""
    def __init__(self, url, username,
                 password) -> None:
        self.client = DirectAdminClient(url, username, password)

    def add_txt_record(self, record_name, record_content, record_ttl=1):
        """Add a TXT record
        :param str record_name: the domain name to add
        :param str record_content: the content of the TXT record to add
        :param int record_ttl: the TTL of the record to add
        """
        try:
            (directadmin_zone, directadmin_name) = self._get_zone_and_name(record_name)
        except DirectAdminClientException as e:
            raise errors.PluginError("Error adding TXT record: %s" % e)

        try:
            response = self.client.add_dns_record(directadmin_zone,
                                                  'txt',
                                                  directadmin_name,
                                                  record_value=record_content,
                                                  record_ttl=record_ttl)

            logger.debug(response)
            if int(response['error']) == 0:
                logger.info("Successfully added TXT record for %s", record_name)
        except DirectAdminClientException as e:
            raise errors.PluginError("Error adding TXT record: %s" % e)

    def del_txt_record(self, record_name, record_content):
        """Remove a TXT record
        :param str record_name: the domain name to remove
        :param str record_content: the content of the TXT record to remove
        """
        (directadmin_zone, directadmin_name) = self._get_zone_and_name(record_name)

        try:
            response = self.client.delete_dns_record(directadmin_zone, 'txt', directadmin_name, record_content)
            logger.debug(response)
            if int(response['error']) == 0:
                logger.info("Successfully removed TXT record for %s", record_name)
        except DirectAdminClientException as e:
            raise errors.PluginError("Error removing TXT record: %s" % e)

    def _get_zone_and_name(self, record_name):
        """Find a suitable zone for a domain
        :param str record_name: the domain name
        :returns: (the zone, the name in the zone)
        :rtype: tuple
        """
        directadmin_name = None
        domains = None
        domains = self.client.get_domain_list()
        for zone in domains:
            if record_name is zone or record_name.endswith('.' + zone):
                directadmin_zone = zone
                directadmin_name = record_name[:-len(zone) - 1]
                break
        if directadmin_name is None:
            raise DirectAdminClientException(
                "Unable to determine DNS Zone from DirectAdmin. \n"
                "Domains: {}\nRecord Name: {}".format(domains,
                                                      record_name)
            )

        if not directadmin_zone:
            raise DirectAdminClientException(
                "Could not get the zone for {}. Is this name in a zone managed in directadmin?".format(record_name))
        logger.debug('Record Domain: ' + record_name)
        logger.debug('Subdomain: ' + directadmin_name)
        logger.debug('Domain: ' + directadmin_zone)
        return directadmin_zone, directadmin_name
