import singer
import singer.utils
import singer.metrics
import dateutil.parser
import pytz

from singer.transform import Transformer, VALID_DATETIME_FORMATS, \
    NO_INTEGER_DATETIME_PARSING, UNIX_SECONDS_INTEGER_DATETIME_PARSING, \
    unix_seconds_to_datetime, unix_milliseconds_to_datetime
from singer.utils import strftime

from tap_framework.streams import BaseStream as base
from tap_campaign_monitor.state import incorporate, save_state, \
    get_last_record_value_for_table

LOGGER = singer.get_logger()


def strptime_with_timezone(dtimestr, timezone):
    d_object = dateutil.parser.parse(dtimestr)

    if d_object.tzinfo is None:
        d_object = timezone.localize(d_object)

    d_object = d_object.astimezone(pytz.UTC)

    return d_object


def string_to_datetime(value, timezone):
    try:
        return strftime(strptime_with_timezone(value, timezone))
    except Exception as ex:
        LOGGER.exception(ex)
        LOGGER.warning("%s, (%s)", ex, value)
        return None


class CampaignMonitorTransformer(Transformer):
    def __init__(self, timezone, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timezone = timezone

    def _transform_datetime(self, value):
        if value is None or value == "":
            return None  # Short circuit in the case of null or empty string

        if self.integer_datetime_fmt not in VALID_DATETIME_FORMATS:
            raise Exception("Invalid integer datetime parsing option")

        if self.integer_datetime_fmt == NO_INTEGER_DATETIME_PARSING:
            return string_to_datetime(value, self.timezone)
        else:
            try:
                if self.integer_datetime_fmt == UNIX_SECONDS_INTEGER_DATETIME_PARSING:  # noqa
                    return unix_seconds_to_datetime(value)
                else:
                    return unix_milliseconds_to_datetime(value)
            except:
                return string_to_datetime(value, self.timezone)


class BaseStream(base):
    KEY_PROPERTIES = ['id']
    API_METHOD = 'GET'

    def transform_record(self, record):
        with CampaignMonitorTransformer(self.client.timezone) as tx:
            metadata = {}

            if self.catalog.metadata is not None:
                metadata = singer.metadata.to_map(self.catalog.metadata)

            return tx.transform(
                record,
                self.catalog.schema.to_dict(),
                metadata)

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
                    [obj])

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
                    [self.incorporate_parent_id(obj, parent)])

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
                        [self.incorporate_parent_id(obj, parent)])

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

        state_key = "{}.{}".format(self.get_parent_id(parent), table)

        start_date = get_last_record_value_for_table(self.state, state_key)

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
                    to_write = self.incorporate_parent_id(obj, parent)

                    singer.write_records(
                        table,
                        [to_write])

                    self.state = incorporate(self.state,
                                             state_key,
                                             'Date',
                                             to_write.get('Date'))

                    counter.increment()

            save_state(self.state)

            if page >= total_pages:
                has_data = False

            else:
                page = page + 1
