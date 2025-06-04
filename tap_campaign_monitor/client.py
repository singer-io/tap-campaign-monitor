import backoff
import requests
import requests.auth
from requests.exceptions import ConnectionError
import singer
import singer.metrics
import time
import pytz

import tap_campaign_monitor.timezones

LOGGER = singer.get_logger()  # noqa


class Server5xxError(Exception):
    pass


class Server429Error(Exception):
    pass


class CampaignMonitorClient:

    def __init__(self, config):
        self.config = config
        self.access_token = self.refresh_access_token()
        self.timezone = self.get_timezone()
        LOGGER.info("Client timezone is {}".format(self.timezone))

    def refresh_access_token(self):
        LOGGER.info("Refreshing access token")
        url = "https://api.createsend.com/oauth/token"
        data = {'grant_type': 'refresh_token', 'refresh_token': self.config['refresh_token']}
        response = requests.request("POST", url, data=data)
        return response.json()['access_token']

    def get_timezone(self):
        url = (
            'https://api.createsend.com/api/v3.2/clients/{}.json'
            .format(self.config.get('client_id'))
        )

        result = self.make_request(url, 'GET')

        timezone = result.get('BasicDetails', {}).get('TimeZone')

        return tap_campaign_monitor.timezones.from_string(timezone)

    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, Server5xxError, Server429Error),
        max_tries=5,
        factor=2,
        on_backoff=lambda details: LOGGER.warning(
            f"Retrying {details['target'].__name__}, attempt {details['tries']}, "
            f"waiting {details['wait']:0.1f}s, after {repr(details['exception'])}"
        )
    )
    def make_request(self, url, method, params=None, body=None):
        LOGGER.info("Making {} request to {}".format(method, url))

        response = requests.request(
            method,
            url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': "Bearer {}".format(self.access_token)
            },
            params=params,
            json=body)

        if response.status_code >= 500:
            raise Server5xxError()
        elif response.status_code == 429:
            raise Server429Error()
        elif response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()
