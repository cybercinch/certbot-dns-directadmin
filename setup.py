from setuptools import setup
from setuptools import find_packages

version = '0.0.14'

with open('README.md') as f:
    readme = f.read()

setup(
    name='certbot-dns-directadmin',
    version=version,
    description='certbot plugin to allow acme dns-01 authentication of a name managed in DirectAdmin.',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/cybercinch/certbot-dns-directadmin',
    author='Aaron Guise',
    author_email='aaron@guise.net.nz',
    license='Apache Licence 2.0',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    keywords='certbot letsencrypt directadmin da dns-01 plugin',
    install_requires=[
        'certbot',
        'zope.interface',
        'tldextract'
    ],
    entry_points={
        'certbot.plugins': [
            'directadmin = certbot_dns_directadmin.dns_directadmin:Authenticator',
        ],
    },
)
