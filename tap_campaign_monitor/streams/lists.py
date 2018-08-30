from tap_campaign_monitor.streams.base import BaseStream


class ListsStream(BaseStream):
    KEY_PROPERTIES = ['ListID']
    TABLE = 'lists'

    @property
    def api_path(self):
        return (
            '/clients/{}/lists.json'
            .format(self.config.get('client_id')))

    def get_stream_data(self, result):
        return [self.transform_record(item)
                for item in result]
