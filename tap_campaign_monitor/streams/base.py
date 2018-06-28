import singer
import singer.utils
import singer.metrics

from funcy import project
from tap_campaign_monitor.schemas import load_schema_by_name
from tap_campaign_monitor.state import incorporate, save_state, \
    get_last_record_value_for_table

LOGGER = singer.get_logger()


class BaseStream:
    # GLOBAL PROPERTIES
    TABLE = None
    KEY_PROPERTIES = ['id']
    API_METHOD = 'GET'
    REQUIRES = []

    def __init__(self, config, state, catalog, client):
        self.config = config
        self.state = state
        self.catalog = catalog
        self.client = client

    def get_schema(self):
        return load_schema_by_name(self.TABLE)

    def get_stream_data(self, result):
        """
        Given a result set from Campaign Monitor, return the data
        to be persisted for this stream.
        """
        raise RuntimeError("get_stream_data not implemented!")

    @classmethod
    def requirements_met(cls, catalog):
        selected_streams = [
            s.stream for s in catalog.streams if s.schema.selected
        ]

        return set(cls.REQUIRES).issubset(selected_streams)

    @classmethod
    def matches_catalog(cls, stream_catalog):
        return stream_catalog.stream == cls.TABLE

    def generate_catalog(self):
        return [{
            'tap_stream_id': self.TABLE,
            'stream': self.TABLE,
            'key_properties': self.KEY_PROPERTIES,
            'schema': self.get_schema()
        }]

    def get_catalog_keys(self):
        return list(self.catalog.schema.properties.keys())

    def filter_keys(self, obj):
        return project(obj, self.get_catalog_keys())

    def write_schema(self):
        singer.write_schema(
            self.catalog.stream,
            self.catalog.schema.to_dict(),
            key_properties=self.catalog.key_properties)

    def sync(self, substreams=None):
        LOGGER.info('Syncing stream {} with {}'
                    .format(self.catalog.tap_stream_id,
                            self.__class__.__name__))

        self.write_schema()

        return self.sync_data(substreams=substreams)

    def sync_data(self, substreams=None):
        if substreams is None:
            substreams = []

        table = self.TABLE
        url = (
            'https://api.createsend.com/api/v3.2{api_path}'.format(
                api_path=self.api_path))

        result = self.client.make_request(url, self.API_METHOD)

        data = self.get_stream_data(result)

        with singer.metrics.record_counter(endpoint=table) as counter:
            for index, obj in enumerate(data):
                LOGGER.info("On {} of {}".format(index, len(data)))

                singer.write_records(
                    table,
                    [self.filter_keys(obj)])

                counter.increment()

                for substream in substreams:
                    substream.sync_data(parent=obj)


class ChildStream(BaseStream):

    def get_parent_id(self, parent):
        raise NotImplementedError('get_parent_id is not implemented!')

    def get_api_path_for_child(self, parent):
        raise NotImplementedError(
            'get_api_path_for_child is not implemented!')

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
            for obj in data:
                singer.write_records(
                    table,
                    [self.filter_keys(
                        self.incorporate_parent_id(obj, parent))])

                counter.increment()


class PaginatedChildStream(ChildStream):

    def sync_data(self, parent=None):
        if parent is None:
            raise RuntimeError('Cannot sync a subobject of null!')

        table = self.TABLE

        has_data = True
        page = 1
        page_size = 1000
        total_pages = -1

        while has_data:
            url = (
                'https://api.createsend.com/api/v3.2{api_path}'.format(
                    api_path=self.get_api_path_for_child(parent)))

            params = {
                'page': page,
                'pagesize': page_size,
            }

            result = self.client.make_request(
                url, self.API_METHOD, params=params)

            total_pages = result.get('NumberOfPages')

            LOGGER.info("Syncing page {} of {}".format(page, total_pages))

            data = self.get_stream_data(result)

            with singer.metrics.record_counter(endpoint=table) as counter:
                for obj in data:
                    singer.write_records(
                        table,
                        [self.filter_keys(
                            self.incorporate_parent_id(obj, parent))])

                    counter.increment()

            if page >= total_pages:
                has_data = False

            else:
                page = page + 1


class DatePaginatedChildStream(ChildStream):

    def sync_data(self, parent=None):
        if parent is None:
            raise RuntimeError('Cannot sync a subobject of null!')

        table = self.TABLE

        has_data = True
        page = 1
        page_size = 1000
        total_pages = -1

        start_date = get_last_record_value_for_table(self.state, table)

        while has_data:
            url = (
                'https://api.createsend.com/api/v3.2{api_path}'.format(
                    api_path=self.get_api_path_for_child(parent)))

            params = {
                'page': page,
                'pagesize': page_size,
                'orderfield': 'date',
                'orderdirection': 'asc',
            }

            if start_date is not None:
                params['date'] = start_date

            result = self.client.make_request(
                url, self.API_METHOD, params=params)

            total_pages = result.get('NumberOfPages')

            LOGGER.info("Syncing page {} of {}".format(page, total_pages))

            data = self.get_stream_data(result)

            with singer.metrics.record_counter(endpoint=table) as counter:
                for obj in data:
                    to_write = self.filter_keys(
                        self.incorporate_parent_id(obj, parent))

                    singer.write_records(
                        table,
                        [to_write])

                    self.state = incorporate(self.state,
                                             table,
                                             'Date',
                                             to_write.get('Date'))

                    counter.increment()

            save_state(self.state)

            if page >= total_pages:
                has_data = False

            else:
                page = page + 1
