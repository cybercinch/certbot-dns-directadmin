"""
The `~certbot-dns-directadmin` plugin automates the process of
completing a ``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and
subsequently removing, TXT records using the DirectAdmin API.


Named Arguments
---------------

========================================  =====================================
``--dns-directadmin-credentials``             DirectAdmin Credentials file.
                                          (Required)
``--dns-directadmin-propagation-seconds``     The number of seconds to wait for DNS
                                          to propagate before asking the ACME
                                          server to verify the DNS record.
                                          (Default: 60)
========================================  =====================================



Credentials
-----------

Use of this plugin requires an account on a DirectAdmin Server.

Supported are both Username/Password authentication or Login Key.


To use Login Key authentication (Recommended) you will need to create a key with 
the following permissions:

* ``CMD_API_LOGIN_TEST``
* ``CMD_API_DNS_CONTROL``
* ``CMD_API_SHOW_DOMAINS``
* ``CMD_API_DOMAIN_POINTER``

DirectAdmin provides instructions for creating a login key - `here <https://help.directadmin.com/item.php?id=523>`_ 


.. code-block:: ini
   :name: directadmin.ini
   :caption: Example credentials file:

   # The DirectAdmin Server url
   # include the scheme and the port number (Normally 2222)
   dns_directadmin_url = https://my.directadminserver.com:2222
   
   # The DirectAdmin username
   dns_directadmin_username = username
   
   # The DirectAdmin password
   dns_directadmin_password = aSuperStrongPasswordorLoginKey

The path to this file can be provided interactively or using the
``--dns-directadmin-credentials`` command-line argument. Certbot records the path
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
     --authenticator dns-directadmin \\
     --dns-directadmin-credentials ~/.secrets/certbot/directadmin.ini \\
     -d example.com

.. code-block:: bash
   :caption: To acquire a single certificate for both ``example.com`` and
             ``www.example.com``

   certbot certonly \\
     --authenticator dns-directadmin \\
     --dns-directadmin-credentials ~/.secrets/certbot/directadmin.ini \\
     -d example.com \\
     -d www.example.com

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``, waiting 120 seconds
             for DNS propagation

   certbot certonly \\
     --authenticator dns-directadmin \\
     --dns-directadmin-credentials ~/.secrets/certbot/directadmin.ini \\
     --dns-directadmin-propagation-seconds 120 \\
     -d example.com

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``, waiting default 60 seconds
             for DNS propagation using docker image

   sudo docker run -it --rm --name certbot \\
        -v "${PWD}/letsencrypt/etc:/etc/letsencrypt" \\
        cybercinch/certbot-dns-directadmin certonly --agree-tos \\
        --authenticator dns-directadmin \\
        --dns-directadmin-credentials=/etc/letsencrypt/credentials.ini \\
        --register-unsafely-without-email \\
        -d example.com

"""
