from tap_campaign_monitor.streams.base import DatePaginatedChildStream


class CampaignBouncesStream(DatePaginatedChildStream):
    KEY_PROPERTIES = ['CampaignID', 'ListID', 'EmailAddress', 'Date']
    TABLE = 'campaign_bounces'
    REQUIRES = ['campaigns']

    def get_parent_id(self, parent):
        return parent.get('CampaignID')

    def incorporate_parent_id(self, obj, parent):
        obj['CampaignID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/campaigns/{}/bounces.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return result.get('Results')
