from tap_campaign_monitor.streams.base import PaginatedChildStream


class CampaignRecipientsStream(PaginatedChildStream):
    KEY_PROPERTIES = ['CampaignID', 'ListID', 'EmailAddress']
    TABLE = 'campaign_recipients'
    REQUIRES = ['campaigns']

    def get_parent_id(self, parent):
        return parent.get('CampaignID')

    def incorporate_parent_id(self, obj, parent):
        obj['CampaignID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/campaigns/{}/recipients.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return result.get('Results')
