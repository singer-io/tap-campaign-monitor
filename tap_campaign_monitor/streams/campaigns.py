from tap_campaign_monitor.streams.base import BaseStream


class CampaignsStream(BaseStream):
    KEY_PROPERTIES = ['CampaignID']
    TABLE = 'campaigns'

    @property
    def api_path(self):
        return (
            '/clients/{}/campaigns.json'
            .format(self.config.get('client_id')))

    def get_stream_data(self, result):
        return result
