from tap_campaign_monitor.streams.base import DatePaginatedChildStream


class ListBouncedSubscribersStream(DatePaginatedChildStream):
    KEY_PROPERTIES = ['ListID', 'EmailAddress', 'Date']
    TABLE = 'list_bounced_subscribers'
    REQUIRES = ['lists']

    def get_parent_id(self, parent):
        return parent.get('ListID')

    def incorporate_parent_id(self, obj, parent):
        obj['ListID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/lists/{}/bounced.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return [self.transform_record(item)
                for item in result.get('Results')]
