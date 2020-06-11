import logging
import tldextract

try:
    #  python 3
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
except ImportError:
    #  python 2
    from urllib import urlencode
    from urllib2 import urlopen, Request

import zope.interface

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common
from certbot_dns_directadmin.directadmin import DirectAdminClient, DirectAdminClientException

logger = logging.getLogger(__name__)


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """directadmin dns-01 authenticator plugin"""

    description = "Obtain a certificate using a DNS TXT record in directadmin"
    problem = "a"

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add, **kwargs):
        super(Authenticator, cls).add_parser_arguments(add, default_propagation_seconds=60)
        add("credentials",
            type=str,
            help="The directadmin credentials INI file")

    def more_info(self):  # pylint: disable=missing-docstring
        return self.description

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'The directadmin credentials INI file',
            {
                'url': 'directadmin url',
                'username': 'directadmin username',
                'password': 'directadmin password'
            }
        )

    def _perform(self, domain, validation_domain_name, validation):
        self._get_directadmin_client().add_txt_record(validation_domain_name, validation)

    def _cleanup(self, domain, validation_domain_name, validation):
        self._get_directadmin_client().del_txt_record(validation_domain_name, validation)

    def _get_directadmin_client(self):
        return _DirectadminClient(
            self.credentials.conf('url'),
            self.credentials.conf('username'),
            self.credentials.conf('password')
        )

        
class _DirectadminClient:
    """Encapsulate communications with the directadmin API"""

    def __init__(self, url, username, password):
        self.url = url
        self.client = DirectAdminClient(url, username, password)

    def add_txt_record(self, record_name, record_content, record_ttl=1):
        """Add a TXT record
        :param str record_name: the domain name to add
        :param str record_content: the content of the TXT record to add
        :param int record_ttl: the TTL of the record to add
        """
        (directadmin_zone, directadmin_name) = self._get_zone_and_name(record_name)

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

    @staticmethod
    def _get_zone_and_name(record_domain):
        """Find a suitable zone for a domain
        :param str record_name: the domain name
        :returns: (the zone, the name in the zone)
        :rtype: tuple
        """

        logger.debug('Record Domain: ' + record_domain)
        (subdomain, domain, suffix) = tldextract.extract(record_domain)
        logger.debug('Subdomain: ' + subdomain)
        logger.debug('Domain: ' + domain)
        logger.debug('Suffix: ' + suffix)

        
        
        # Check if subdomain has a period
        if "." in subdomain:
            # This is second-level subdomain
            ml = subdomain.split('.')
            directadmin_zone = "."join(ml.pop(), domain, suffix)
            directadmin_name = ml[0]
        else
            # Single Level subdomain ;)
            directadmin_name = subdomain
            directadmin_zone = ".".join((domain, suffix))

        return directadmin_zone, directadmin_name
