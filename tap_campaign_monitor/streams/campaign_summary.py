from tap_campaign_monitor.streams.base import ChildStream

import singer


class CampaignSummaryStream(ChildStream):
    KEY_PROPERTIES = ['CampaignID']
    TABLE = 'campaign_summary'
    REQUIRES = ['campaigns']

    def get_parent_id(self, parent):
        return parent.get('CampaignID')

    def incorporate_parent_id(self, obj, parent):
        obj['CampaignID'] = self.get_parent_id(parent)
        return obj

    def get_api_path_for_child(self, parent):
        return (
            '/campaigns/{}/summary.json'
            .format(self.get_parent_id(parent)))

    def get_stream_data(self, result):
        return result

    def sync_data(self, parent=None):
        if parent is None:
            raise RuntimeError('Cannot sync a subobject of null!')

        table = self.TABLE
        url = (
            'https://api.createsend.com/api/v3.2{api_path}'.format(
                api_path=self.get_api_path_for_child(parent)))

        result = self.client.make_request(url, self.API_METHOD)

        data = self.get_stream_data(result)

        with singer.metrics.record_counter(endpoint=table) as counter:
            singer.write_records(
                table,
                [self.filter_keys(
                    self.incorporate_parent_id(data, parent))])

            counter.increment()
