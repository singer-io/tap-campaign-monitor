from tap_campaign_monitor.streams.base import DatePaginatedChildStream


class CampaignOpensStream(DatePaginatedChildStream):
    KEY_PROPERTIES = ['CampaignID', 'ListID', 'EmailAddress', 'Date']
    TABLE = 'campaign_opens'
    REQUIRES = ['campaigns']

    def get_parent_id(self, parent):
        return parent.get('CampaignID')

    def incorporate_parent_id(self, obj, parent):
        obj['CampaignID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/campaigns/{}/opens.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return [self.transform_record(item)
                for item in result.get('Results')]
