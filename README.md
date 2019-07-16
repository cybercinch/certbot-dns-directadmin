# certbot-dns-directadmin

Plugin to allow acme dns-01 authentication of a name managed in DirectAdmin. Useful for automating and creating a Let's Encrypt certificate (wildcard or not) for a service with a name managed by DirectAdmin, but installed on a server not managed in DirectAdmin.

## How to use
### 1. Install
First, install certbot and the plugin using pip:
```
pip install certbot certbot-dns-directadmin
```
### 2. Configure
Download the file `credentials.ini.example` and rename it to `directadmin-credentials.ini`. Edit it to set your DirectAdmin url, username and password.
```
# The url DirectAdmin url
# include the scheme and the port number (usually 2222)
certbot_dns_directadmin:directadmin_url = https://directadmin.example.com:2222
# The DirectAdmin username
certbot_dns_directadmin:directadmin_username = user

# The DirectAdmin password
certbot_dns_directadmin:directadmin_password = hunter2
```
### 3. Run
You can now run certbot using the plugin and feeding the credentials file.  
For example, to get a certificate for example.com and www.example.com:
```
certbot certonly \
--authenticator certbot-dns-directadmin:directadmin \
--certbot-dns-directadmin:panel-credentials /path/to/directadmin-credentials.ini \
-d example.com \
-d www.example.com
```
To create a wildcard certificate *.example.com and install it on an apache server, the installer plugin must be specified with the `--installer` option.
You will need to install the apache plugin if it's not already present on your system.
```
pip install certbot-apache
certbot run \
--apache \
--authenticator certbot-dns-directadmin:directadmin \
--installer apache \
--certbot-dns-directadmin:directadmin-credentials /path/to/directadmin-credentials.ini \
-d '*.example.com'
```
The certbot documentation has some additionnal informations about combining authenticator and installer plugins: https://certbot.eff.org/docs/using.html#getting-certificates-and-choosing-plugins

## Docker
A docker image based on [certbot/certbot](https://hub.docker.com/r/certbot/certbot/) is provided for your convenience:
```
docker run \
-v /path/to/credentials.ini:/tmp/credentials.ini \
cybercinch/certbot-dns-directadmin \
certonly \
--authenticator certbot-dns-directadmin:directadmin \
--certbot-dns-cpanel:cpanel-credentials /tmp/directadmin-credentials.ini \
-d example.com \
-d www.example.com
```

## Additional documentation
* https://certbot.eff.org/docs/
