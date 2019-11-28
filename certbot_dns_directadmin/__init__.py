"""
The `~certbot-dns-directadmin:directadmin` plugin automates the process of
completing a ``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and
subsequently removing, TXT records using the DirectAdmin API.


Named Arguments
---------------

===============================================================   ==========================================
``--certbot-dns-directadmin:directadmin-credentials``             DirectAdmin Credentials file. (Required)
``--certbot-dns-directadmin:directadmin-propagation-seconds``     The number of seconds to wait for DNS to
                                                                  propagate before asking the ACME server
                                                                  to verify the DNS record. (Default: 60)
===============================================================   ==========================================


Credentials
-----------

Use of this plugin requires an account on a DirectAdmin Server.

Supported are both Username/Password authentication or Login Key.


To use Login Key authentication (Recommended) you will need to create a key with 
the following permissions:

* ``CMD_API_LOGIN_TEST``
* ``CMD_API_DNS_CONTROL``
* ``CMD_API_SHOW_DOMAINS``

DirectAdmin provides instructions for creating a login key - `here <https://help.directadmin.com/item.php?id=523>`_ 


.. code-block:: ini
   :name: directadmin.ini
   :caption: Example credentials file:

   # The DirectAdmin Server url
   # include the scheme and the port number (Normally 2222)
   certbot_dns_directadmin:directadmin_url = https://my.directadminserver.com:2222
   
   # The DirectAdmin username
   certbot_dns_directadmin:directadmin_username = username
   
   # The DirectAdmin password
   certbot_dns_directadmin:directadmin_password = aSuperStrongPassword

The path to this file can be provided interactively or using the
``--certbot-dns-directadmin:directadmin-credentials`` command-line argument. Certbot records the path
to this file for use during renewal, but does not store the file's contents.

.. caution::
   You should protect these API credentials as you would a password. Users who
   can read this file can use these credentials to issue some types of API calls
   on your behalf, limited by the permissions assigned to the account. Users who
   can cause Certbot to run using these credentials can complete a ``dns-01``
   challenge to acquire new certificates or revoke existing certificates for
   domains these credentials are authorized to manage.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).


Examples
--------

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``

   certbot certonly \\
     --authenticator certbot-dns-directadmin:directadmin \\
     --certbot-dns-directadmin:directadmin-credentials ~/.secrets/certbot/directadmin.ini \\
     -d example.com

.. code-block:: bash
   :caption: To acquire a single certificate for both ``example.com`` and
             ``www.example.com``

   certbot certonly \\
     --authenticator certbot-dns-directadmin:directadmin \\
     --certbot-dns-directadmin:directadmin-credentials ~/.secrets/certbot/directadmin.ini \\
     -d example.com \\
     -d www.example.com

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``, waiting 120 seconds
             for DNS propagation

   certbot certonly \\
     --authenticator certbot-dns-directadmin:directadmin \\
     --certbot-dns-directadmin:directadmin-credentials ~/.secrets/certbot/directadmin.ini \\
     --certbot-dns-directadmin:directadmin-propagation-seconds 120 \\
     -d example.com

"""

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

        directadmin_zone = ".".join((domain, suffix))
        directadmin_name = subdomain

        return directadmin_zone, directadmin_name
