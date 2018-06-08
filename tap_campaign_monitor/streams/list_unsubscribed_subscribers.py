from tap_campaign_monitor.streams.base import DatePaginatedChildStream


class ListUnsubscribedSubscribersStream(DatePaginatedChildStream):
    KEY_PROPERTIES = ['ListID', 'EmailAddress', 'Date']
    TABLE = 'list_unsubscribed_subscribers'
    REQUIRES = ['lists']

    def get_parent_id(self, parent):
        return parent.get('ListID')

    def incorporate_parent_id(self, obj, parent):
        obj['ListID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/lists/{}/unsubscribed.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return result.get('Results')
