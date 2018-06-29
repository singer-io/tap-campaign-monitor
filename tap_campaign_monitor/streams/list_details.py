from tap_campaign_monitor.streams.base import ChildStream


class ListDetailsStream(ChildStream):
    KEY_PROPERTIES = ['ListID']
    TABLE = 'list_details'
    REQUIRES = ['lists']

    def get_parent_id(self, parent):
        return parent.get('ListID')

    def incorporate_parent_id(self, obj, parent):
        obj['ListID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/lists/{}.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return result
