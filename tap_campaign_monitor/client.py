import backoff
import requests
import requests.auth
from requests.exceptions import ConnectionError
import singer
import singer.metrics
from time import sleep
import pytz

import tap_campaign_monitor.timezones

RETRY_RATE_LIMIT = 360

LOGGER = singer.get_logger()  # noqa


class Server5xxError(Exception):
    pass


class Server429Error(Exception):
    def __init__(self, message=None, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


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
        backoff.constant,
        Server429Error,
        max_tries=5,
        on_backoff=lambda details: (
            LOGGER.warning(
                f"[RateLimit] Retrying {details['target'].__name__}, attempt {details['tries']}, "
                f"waiting {details['exception'].retry_after or 0}s due to rate limit {repr(details['exception'])}"
            ),
            sleep(details['exception'].retry_after or 0)
        ),
    )
    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, Server5xxError),
        max_tries=5,
        on_backoff=lambda details: LOGGER.warning(
            f"[Retryable] Retrying {details['target'].__name__}, attempt {details['tries']}, "
            f"waiting {details['wait']:0.1f}s due to {repr(details['exception'])}"
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

        if response.status_code >= 500  and response.status_code < 600:
            raise Server5xxError()
        elif response.status_code == 429:
            try:
                retry_after = int(float(response.headers.get("X-RateLimit-Reset", RETRY_RATE_LIMIT)))
            except (TypeError, ValueError):
                retry_after = RETRY_RATE_LIMIT
            raise Server429Error(retry_after=retry_after)
        elif response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()
