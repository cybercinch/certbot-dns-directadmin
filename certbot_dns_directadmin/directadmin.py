import json
import logging
import base64
from collections import OrderedDict
import requests

# noinspection PyUnresolvedReferences
try:
    #  python 3
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, parse_qs
except ImportError:
    # noinspection PyUnresolvedReferences
    #  python 2
    from urllib import urlencode
    from urllib2 import urlopen, Request
    from cgi import parse_qs

logger = logging.getLogger(__name__)


class DirectAdminClient:

    def __init__(self, url, username, password):

        self.version = "0.0.7"
        self.client = requests.session()
        self.headers = {
            "user-agent": "pyDirectAdmin/" + str(self.version),
            "Authorization": "Basic %s"
            % base64.b64encode(("%s:%s" % (username, password)).encode()).decode(
                "utf8"
            ),
        }
        self.url = url

    def make_request(self, endpoint, data=None):
        response = None  # Empty response variable

        if data is not None:
            #  Data is present add the fields to call
            response = urlopen(
                Request(
                    "%s?%s" % (self.url + "/{}".format(endpoint), urlencode(data)),
                    headers=self.headers,
                )
            )
        elif data is None:
            #  Data is not present so we don't need addition field.
            response = urlopen(
                Request(
                    "%s?" % (self.url + "/{}".format(endpoint)),
                    headers=self.headers,
                )
            )

        return response

    @staticmethod
    def _process_response(response):
        logger.debug("Processing Response")
        if int(response["error"][0]) > 0:
            # There was an error
            raise DirectAdminClientException(response["text"][0])
        elif int(response["error"][0]) == 0:
            # Everything succeeded
            return {"error": response["error"][0], "message": response["text"][0]}

    def get_domain_list(self):
        r = self.make_request("CMD_API_SHOW_DOMAINS")

        domains = parse_qs(
            r.read().decode("utf8"), keep_blank_values=0, strict_parsing=1
        )

        domain_list = dict()
        for key, value in domains.items():
            # Extract domain list
            response = value
            logger.debug("Domains returned " + json.dumps(response))
            for domain in response:
                domain_list.update({domain: domain})
                r = self.make_request(
                    "CMD_API_DOMAIN_POINTER", OrderedDict([("domain", domain)])
                )
                try:
                    pointers = parse_qs(
                        r.read().decode("utf8"), keep_blank_values=0, strict_parsing=1
                    )
                    for pointer in pointers.keys():
                        domain_list.update({pointer: domain})
                except ValueError:
                    # Probably a domain no pointers
                    pass
        return domain_list

    def get_zone_list(self, domain):
        params = OrderedDict([("domain", domain)])
        r = self.make_request("CMD_API_DNS_CONTROL", params)

        return r.read()

    def add_dns_record(
        self,
        domain,
        record_type,
        record_name,
        record_value,
        record_ttl=None,
        affect_pointers="no",
    ):

        params = OrderedDict(
            [
                ("domain", domain),
                ("action", "add"),
                ("type", record_type.upper()),
                ("name", record_name),
                ("value", record_value),
                ("affect_pointers", affect_pointers),
            ]
        )

        if record_ttl is not None:
            params.update({"ttl": record_ttl})

        response = self.make_request("CMD_API_DNS_CONTROL", data=params)
        response = parse_qs(
            response.read().decode("utf8"), keep_blank_values=0, strict_parsing=1
        )

        return self._process_response(response)

    def update_dns_record(
        self,
        domain,
        record_type,
        record_name,
        record_value_old,
        record_value_new,
        record_ttl=None,
    ):

        params = OrderedDict(
            [
                ("domain", domain),
                ("action", "edit"),
                ("type", record_type.upper()),
                (
                    record_type.lower() + "recs0",
                    "name={}&value={}".format(record_name, record_value_old),
                ),
                ("name", record_name),
                ("value", record_value_new),
            ]
        )

        if record_ttl is not None:
            params.update({"ttl": record_ttl})

        response = self.make_request("CMD_API_DNS_CONTROL", data=params)
        response = parse_qs(
            response.read().decode("utf8"), keep_blank_values=0, strict_parsing=1
        )

        return self._process_response(response)

    def delete_dns_record(
        self, domain, record_type, record_name, record_value, affect_pointers="no"
    ):
        params = OrderedDict(
            [
                ("domain", domain),
                ("action", "select"),
                (
                    record_type.lower() + "recs0",
                    "name={}&value={}".format(record_name, record_value),
                ),
                ("affect_pointers", affect_pointers),
            ]
        )

        response = self.make_request("CMD_API_DNS_CONTROL", data=params)
        response = parse_qs(
            response.read().decode("utf8"), keep_blank_values=0, strict_parsing=1
        )
        logger.debug("Del Response: " + json.dumps(response))
        return self._process_response(response)

    def override_domain_ttl(self, domain, record_name, ttl):
        params = OrderedDict(
            [
                ("domain", domain),
                ("action", "ttl"),
                ("ttl_select", "custom"),
                ("name", record_name),
                ("ttl", ttl),
            ]
        )

        response = self.make_request("CMD_API_DNS_CONTROL", data=params)
        response = parse_qs(
            response.read().decode("utf8"), keep_blank_values=0, strict_parsing=1
        )

        return self._process_response(response)


class DirectAdminClientException(Exception):
    pass
