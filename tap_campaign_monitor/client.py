import requests
import requests.auth
import singer
import singer.metrics
import time

LOGGER = singer.get_logger()  # noqa


class CampaignMonitorClient:

    def __init__(self, config):
        self.config = config

    def get_authorization(self):
        return requests.auth.HTTPBasicAuth(
            self.config.get('api_key'),
            'x')

    def make_request(self, url, method, base_backoff=30,
                     params=None, body=None):
        auth = self.get_authorization()

        LOGGER.info("Making {} request to {}".format(method, url))

        response = requests.request(
            method,
            url,
            headers={
                'Content-Type': 'application/json'
            },
            auth=auth,
            params=params,
            json=body)

        if response.status_code in [429, 504]:
            if base_backoff > 120:
                raise RuntimeError('Backed off too many times, exiting!')

            LOGGER.warn('Sleeping for {} seconds and trying again'
                        .format(base_backoff))

            time.sleep(base_backoff)

            return self.make_request(
                url, method, base_backoff * 2, params, body)

        elif response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()
