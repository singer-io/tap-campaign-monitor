import requests
import requests.auth
import singer
import singer.metrics

LOGGER = singer.get_logger()  # noqa


class CampaignMonitorClient:

    def __init__(self, config):
        self.config = config

    def get_authorization(self):
        return requests.auth.HTTPBasicAuth(
            self.config.get('api_key'),
            'x')

    def make_request(self, url, method, params=None, body=None):
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

        if response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()
