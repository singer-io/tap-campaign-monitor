import backoff
import requests
import requests.auth
from requests.exceptions import ChunkedEncodingError, ConnectionError, Timeout
import singer
import singer.metrics
import time
import pytz

import tap_campaign_monitor.timezones

RETRY_RATE_LIMIT = 360

LOGGER = singer.get_logger()  # noqa


class Server5xxError(Exception):
    pass


class Server429Error(Exception):
    pass


class CampaignMonitorForbiddenError(Exception):
    pass


class CampaignMonitorClient:

    def __init__(self, config):
        self.config = config
        self._retry_after = RETRY_RATE_LIMIT
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

    def _rate_limit_backoff(self):
        """
        Bound wait‐generator: on each retry backoff will call next()
        and sleep for self._retry_after seconds.
        """
        while True:
            yield self._retry_after

    def make_request(self, url, method, params=None, body=None):
        @backoff.on_exception(
            self._rate_limit_backoff,
            Server429Error,
            max_tries=5,
            jitter=None,
        )
        @backoff.on_exception(
            backoff.expo,
            (ConnectionError, Server5xxError, Timeout, ChunkedEncodingError),
            max_tries=5,
        )
        def _call():
            LOGGER.info("Making {} request to {}".format(method, url))

            resp = requests.request(
                method,
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {}".format(self.access_token),
                },
                params=params,
                json=body,
            )

            if resp.status_code >= 500 and resp.status_code < 600:
                raise Server5xxError()
            elif resp.status_code == 429:
                try:
                    self._retry_after = int(
                        float(resp.headers.get("X-RateLimit-Reset", RETRY_RATE_LIMIT))
                    )
                except (TypeError, ValueError):
                    self._retry_after = RETRY_RATE_LIMIT
                raise Server429Error()
            elif resp.status_code in (401, 403):
                raise CampaignMonitorForbiddenError(resp.text)
            elif resp.status_code != 200:
                raise RuntimeError(resp.text)

            return resp

        response = _call()
        return response.json()
