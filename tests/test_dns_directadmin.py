import unittest
from contextlib import contextmanager
from unittest import mock

from certbot import errors
from certbot.compat import os
from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN
from certbot.tests import util as test_util

from certbot_dns_directadmin.dns_directadmin import Authenticator
from certbot_dns_directadmin.directadmin import DirectAdminClientException

API_ERROR = DirectAdminClientException('Test Client Exception')
API_URL = "https://somedaserver:2222"
API_USERNAME = 'an-api-username'
API_PASSWORD = 'an-api-key'


class AuthenticatorTest(test_util.TempDirTestCase, dns_test_common.BaseAuthenticatorTest):

    def setUp(self):

        super().setUp()

        path = os.path.join(self.tempdir, 'file.ini')
        dns_test_common.write({"directadmin_url": API_URL,
                               "directadmin_username": API_USERNAME,
                               "directadmin_password": API_PASSWORD}, path)

        self.config = mock.MagicMock(directadmin_credentials=path,
                                     directadmin_propagation_seconds=0)  # don't wait during tests

        self.auth = Authenticator(self.config, "directadmin")

        self.mock_client = mock.MagicMock()
        # _get_directadmin_client | pylint: disable=protected-access
        self.auth._get_directadmin_client = mock.MagicMock(return_value=self.mock_client)

    @test_util.patch_display_util()
    def test_perform(self, unused_mock_get_utility):
        dns_test_common.write({"directadmin_url": API_URL,
                               "directadmin_username": API_USERNAME,
                               "directadmin_password": API_PASSWORD}, self.config.directadmin_credentials)
        self.auth.perform([self.achall])

        expected = [mock.call.add_txt_record('_acme-challenge.' + DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)

    def test_cleanup(self):
        # _attempt_cleanup | pylint: disable=protected-access
        self.auth._attempt_cleanup = True
        self.auth.cleanup([self.achall])

        expected = [mock.call.del_txt_record('_acme-challenge.' + DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)

    def test_no_creds(self):
        dns_test_common.write({}, self.config.directadmin_credentials)
        self.assertRaises(errors.PluginError,
                          self.auth.perform,
                          [self.achall])

    def test_missing_username_or_password_or_token(self):
        dns_test_common.write({"directadmin_url": API_URL,
                               "directadmin_username": API_USERNAME},
                              self.config.directadmin_credentials)
        self.assertRaises(errors.PluginError,
                          self.auth.perform,
                          [self.achall])


class DirectadminClientTest(unittest.TestCase):
    record_name = "foo"
    record_content = "bar"
    record_ttl = 42
    domain_name = "example.com"

    @contextmanager
    def assertNotRaises(self, exc_type):
        try:
            yield None
        except exc_type:
            raise self.failureException('{} raised'.format(exc_type.__name__))

    @staticmethod
    def _assertNotRaises(exception, obj, attr):
        try:
            result = getattr(obj, attr)
            if hasattr(result, '__call__'):
                result()
        except Exception as e:
            if isinstance(e, exception):
                raise AssertionError('{}.{} raises {}.'.format(obj, attr, exception))

    def setUp(self):
        from certbot_dns_directadmin.dns_directadmin import _DirectadminClient

        self.directadmin_client = _DirectadminClient(API_URL, API_USERNAME, API_PASSWORD)

        self.client = mock.MagicMock()
        self.client.get_domain_list.return_value = dict()
        self.client.get_domain_list.return_value.update({'example.com': 'example.com'})
        self.directadmin_client.client = self.client

    def tearDown(self):
        self.client.get_domain_list.return_value = None

    def test_add_txt_record(self):
        self.client._get_zone_and_name.return_value = (self.record_name, self.domain_name, 'no')
        self.directadmin_client.client.add_dns_record.return_value = {'error': 0}
        self.directadmin_client.add_txt_record(".".join([self.record_name,
                                                         DOMAIN]),
                                               self.record_content,
                                               self.record_ttl)
        self.client.add_dns_record.assert_called_with(self.domain_name,
                                                      'txt',
                                                      self.record_name,
                                                      record_value=self.record_content,
                                                      record_ttl=self.record_ttl,
                                                      affect_pointers='no')

    def test_add_txt_record_unable_to_find_zone(self):
        self.client.get_domain_list.return_value = dict()
        self.client.get_domain_list.return_value.update({'notexample.com': 'notexample.com'})

        self.assertRaises(
            errors.PluginError, lambda: self.directadmin_client.add_txt_record(
                ".".join([self.record_name,
                          self.domain_name]), self.record_content, self.record_ttl))

    def test_del_txt_record(self):
        self.client.get_domain_list.return_value = dict()
        self.client.get_domain_list.return_value.update({'example.com': 'example.com'})
        self.directadmin_client.client.delete_dns_record.return_value = {'error': 0}
        self.directadmin_client.del_txt_record(".".join([self.record_name,
                                                         self.domain_name]),
                                               self.record_content)


# Not Called
# self.client.add_dns_record.assert_called_with(self.domain_name,
#                                               'txt',
#                                               self.record_name,
#                                               record_value=self.record_content,
#                                               record_ttl=self.record_ttl)

# def test_add_txt_record_error_during_zone_lookup(self):
#     self.cf.zones.get.side_effect = API_ERROR
#
#     self.assertRaises(
#         errors.PluginError,
#         self.cloudflare_client.add_txt_record,
#         DOMAIN, self.record_name, self.record_content, self.record_ttl)
#
# def test_add_txt_record_zone_not_found(self):
#     self.cf.zones.get.return_value = []
#
#     self.assertRaises(
#         errors.PluginError,
#         self.cloudflare_client.add_txt_record,
#         DOMAIN, self.record_name, self.record_content, self.record_ttl)
#
# def test_add_txt_record_bad_creds(self):
#     self.client.get_domain_list.side_effect = DirectAdminClientException('Bad Credentials!')
#     self.assertRaises(
#         errors.PluginError,
#         self.directadmin_client.add_txt_record,
#         self.record_name + '.' + DOMAIN, self.record_content, self.record_ttl)
#
# def test_del_txt_record(self):
#     self.cf.zones.get.return_value = [{'id': self.zone_id}]
#     self.cf.zones.dns_records.get.return_value = [{'id': self.record_id}]
#
#     self.cloudflare_client.del_txt_record(DOMAIN, self.record_name, self.record_content)
#
#     expected = [mock.call.zones.get(params=mock.ANY),
#                 mock.call.zones.dns_records.get(self.zone_id, params=mock.ANY),
#                 mock.call.zones.dns_records.delete(self.zone_id, self.record_id)]
#
#     self.assertEqual(expected, self.cf.mock_calls)
#
#     get_data = self.cf.zones.dns_records.get.call_args[1]['params']
#
#     self.assertEqual('TXT', get_data['type'])
#     self.assertEqual(self.record_name, get_data['name'])
#     self.assertEqual(self.record_content, get_data['content'])
#
# def test_del_txt_record_error_during_zone_lookup(self):
#     self.cf.zones.get.side_effect = API_ERROR
#
#     self.cloudflare_client.del_txt_record(DOMAIN, self.record_name, self.record_content)
#
# def test_del_txt_record_error_during_delete(self):
#     self.cf.zones.get.return_value = [{'id': self.zone_id}]
#     self.cf.zones.dns_records.get.return_value = [{'id': self.record_id}]
#     self.cf.zones.dns_records.delete.side_effect = API_ERROR
#
#     self.cloudflare_client.del_txt_record(DOMAIN, self.record_name, self.record_content)
#     expected = [mock.call.zones.get(params=mock.ANY),
#                 mock.call.zones.dns_records.get(self.zone_id, params=mock.ANY),
#                 mock.call.zones.dns_records.delete(self.zone_id, self.record_id)]
#
#     self.assertEqual(expected, self.cf.mock_calls)
#
# def test_del_txt_record_error_during_get(self):
#     self.cf.zones.get.return_value = [{'id': self.zone_id}]
#     self.cf.zones.dns_records.get.side_effect = API_ERROR
#
#     self.cloudflare_client.del_txt_record(DOMAIN, self.record_name, self.record_content)
#     expected = [mock.call.zones.get(params=mock.ANY),
#                 mock.call.zones.dns_records.get(self.zone_id, params=mock.ANY)]
#
#     self.assertEqual(expected, self.cf.mock_calls)
#
# def test_del_txt_record_no_record(self):
#     self.cf.zones.get.return_value = [{'id': self.zone_id}]
#     self.cf.zones.dns_records.get.return_value = []
#
#     self.cloudflare_client.del_txt_record(DOMAIN, self.record_name, self.record_content)
#     expected = [mock.call.zones.get(params=mock.ANY),
#                 mock.call.zones.dns_records.get(self.zone_id, params=mock.ANY)]
#
#     self.assertEqual(expected, self.cf.mock_calls)
#
# def test_del_txt_record_no_zone(self):
#     self.cf.zones.get.return_value = [{'id': None}]
#
#     self.cloudflare_client.del_txt_record(DOMAIN, self.record_name, self.record_content)
#     expected = [mock.call.zones.get(params=mock.ANY)]
#
#     self.assertEqual(expected, self.cf.mock_calls)


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
