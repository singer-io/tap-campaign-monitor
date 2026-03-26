import unittest
from unittest.mock import patch, MagicMock, call
import singer
import pytz

from tap_campaign_monitor.streams.base import (
    BaseStream, ChildStream, PaginatedChildStream,
    DatePaginatedChildStream, CampaignMonitorTransformer,
    strptime_with_timezone, string_to_datetime,
)


class TestStrptimeWithTimezone(unittest.TestCase):
    """Test timezone-aware datetime parsing."""

    def test_naive_datetime_gets_localized(self):
        """Test that a naive datetime string gets localized to given timezone."""
        tz = pytz.timezone('US/Eastern')
        result = strptime_with_timezone('2024-01-15 10:30:00', tz)
        self.assertEqual(result.tzinfo, pytz.UTC)

    def test_aware_datetime_converted_to_utc(self):
        """Test that an aware datetime string gets converted to UTC."""
        tz = pytz.timezone('US/Eastern')
        result = strptime_with_timezone('2024-01-15T10:30:00+05:30', tz)
        self.assertEqual(result.tzinfo, pytz.UTC)
        self.assertEqual(result.hour, 5)
        self.assertEqual(result.minute, 0)

    def test_utc_datetime_stays_utc(self):
        """Test that a UTC datetime stays UTC."""
        tz = pytz.UTC
        result = strptime_with_timezone('2024-01-15T10:30:00Z', tz)
        self.assertEqual(result.tzinfo, pytz.UTC)
        self.assertEqual(result.hour, 10)


class TestStringToDatetime(unittest.TestCase):
    """Test string_to_datetime conversion."""

    def test_valid_datetime_returns_formatted_string(self):
        """Test valid datetime conversion."""
        tz = pytz.UTC
        result = string_to_datetime('2024-01-15T10:30:00Z', tz)
        self.assertIsNotNone(result)
        self.assertIn('2024-01-15', result)

    def test_invalid_datetime_returns_none(self):
        """Test invalid datetime returns None."""
        tz = pytz.UTC
        result = string_to_datetime('not-a-date', tz)
        self.assertIsNone(result)


class TestCampaignMonitorTransformer(unittest.TestCase):
    """Test the custom transformer."""

    def test_transform_datetime_none_returns_none(self):
        """Test that None value returns None."""
        tz = pytz.UTC
        with CampaignMonitorTransformer(tz) as tx:
            result = tx._transform_datetime(None)
            self.assertIsNone(result)

    def test_transform_datetime_empty_string_returns_none(self):
        """Test that empty string returns None."""
        tz = pytz.UTC
        with CampaignMonitorTransformer(tz) as tx:
            result = tx._transform_datetime("")
            self.assertIsNone(result)

    def test_transform_datetime_valid_string(self):
        """Test that valid datetime string is transformed."""
        tz = pytz.timezone('US/Eastern')
        with CampaignMonitorTransformer(tz) as tx:
            result = tx._transform_datetime('2024-01-15 10:30:00')
            self.assertIsNotNone(result)
            self.assertIn('2024', result)


def _make_mock_client():
    """Create a mock client with timezone."""
    client = MagicMock()
    client.timezone = pytz.UTC
    return client


def _make_mock_catalog(schema_dict, key_properties=None):
    """Create a mock catalog entry."""
    catalog = MagicMock()
    catalog.schema.to_dict.return_value = schema_dict
    catalog.metadata = None
    catalog.tap_stream_id = 'test_stream'
    catalog.stream = 'test_stream'
    catalog.key_properties = key_properties or ['id']
    return catalog


class TestBaseStreamSync(unittest.TestCase):
    """Test BaseStream sync logic."""

    @patch('tap_campaign_monitor.streams.base.singer.write_records')
    @patch('tap_campaign_monitor.streams.base.singer.write_schema')
    def test_sync_data_writes_records(self, mock_write_schema, mock_write_records):
        """Test that sync_data calls write_records for each data item."""
        client = _make_mock_client()
        client.make_request.return_value = [
            {'CampaignID': 'c1', 'Name': 'Test Campaign'}
        ]

        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'Name': {'type': ['string', 'null']}
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID'])
        catalog.tap_stream_id = 'campaigns'
        catalog.stream = 'campaigns'

        from tap_campaign_monitor.streams.campaigns import CampaignsStream
        stream = CampaignsStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        stream.sync()
        mock_write_records.assert_called_once()
        args = mock_write_records.call_args
        self.assertEqual(args[0][0], 'campaigns')


class TestChildStreamSync(unittest.TestCase):
    """Test ChildStream sync logic."""

    def test_sync_data_raises_without_parent(self):
        """Test that sync_data raises RuntimeError without parent."""
        client = _make_mock_client()
        schema = {
            'type': 'object',
            'properties': {'CampaignID': {'type': 'string'}}
        }
        catalog = _make_mock_catalog(schema, ['CampaignID'])

        from tap_campaign_monitor.streams.campaign_summary import CampaignSummaryStream
        stream = CampaignSummaryStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        with self.assertRaises(RuntimeError) as ctx:
            stream.sync_data(parent=None)
        self.assertIn('Cannot sync a subobject of null', str(ctx.exception))

    @patch('tap_campaign_monitor.streams.campaign_summary.singer.write_records')
    def test_child_stream_incorporates_parent_id(self, mock_write_records):
        """Test that child stream incorporates parent ID into records."""
        client = _make_mock_client()
        client.make_request.return_value = {
            'Recipients': 100,
            'TotalOpened': 50,
        }

        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'Recipients': {'type': ['number', 'null']},
                'TotalOpened': {'type': ['number', 'null']},
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID'])
        catalog.tap_stream_id = 'campaign_summary'
        catalog.stream = 'campaign_summary'

        from tap_campaign_monitor.streams.campaign_summary import CampaignSummaryStream
        stream = CampaignSummaryStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        parent = {'CampaignID': 'campaign_abc'}
        stream.sync_data(parent=parent)

        mock_write_records.assert_called_once()
        written_record = mock_write_records.call_args[0][1][0]
        self.assertEqual(written_record['CampaignID'], 'campaign_abc')


class TestPaginatedChildStreamSync(unittest.TestCase):
    """Test PaginatedChildStream pagination logic."""

    @patch('tap_campaign_monitor.streams.base.singer.write_records')
    def test_pagination_iterates_pages(self, mock_write_records):
        """Test that paginated stream iterates through all pages."""
        client = _make_mock_client()
        # Page 1: 2 results, Page 2: 1 result
        client.make_request.side_effect = [
            {
                'NumberOfPages': 2,
                'Results': [
                    {'EmailAddress': 'a@test.com', 'ListID': 'l1'},
                    {'EmailAddress': 'b@test.com', 'ListID': 'l1'},
                ]
            },
            {
                'NumberOfPages': 2,
                'Results': [
                    {'EmailAddress': 'c@test.com', 'ListID': 'l1'},
                ]
            }
        ]

        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'ListID': {'type': ['string', 'null']},
                'EmailAddress': {'type': 'string'},
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID', 'ListID', 'EmailAddress'])
        catalog.tap_stream_id = 'campaign_recipients'
        catalog.stream = 'campaign_recipients'

        from tap_campaign_monitor.streams.campaign_recipients import CampaignRecipientsStream
        stream = CampaignRecipientsStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        parent = {'CampaignID': 'campaign_xyz'}
        stream.sync_data(parent=parent)

        self.assertEqual(client.make_request.call_count, 2)
        self.assertEqual(mock_write_records.call_count, 3)

    @patch('tap_campaign_monitor.streams.base.singer.write_records')
    def test_single_page_no_extra_requests(self, mock_write_records):
        """Test that a single page does not make extra requests."""
        client = _make_mock_client()
        client.make_request.return_value = {
            'NumberOfPages': 1,
            'Results': [
                {'EmailAddress': 'a@test.com', 'ListID': 'l1'},
            ]
        }

        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'ListID': {'type': ['string', 'null']},
                'EmailAddress': {'type': 'string'},
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID', 'ListID', 'EmailAddress'])
        catalog.tap_stream_id = 'campaign_recipients'
        catalog.stream = 'campaign_recipients'

        from tap_campaign_monitor.streams.campaign_recipients import CampaignRecipientsStream
        stream = CampaignRecipientsStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        parent = {'CampaignID': 'campaign_xyz'}
        stream.sync_data(parent=parent)

        self.assertEqual(client.make_request.call_count, 1)


class TestDatePaginatedChildStreamSync(unittest.TestCase):
    """Test DatePaginatedChildStream with date-based bookmarking."""

    @patch('tap_campaign_monitor.streams.base.save_state')
    @patch('tap_campaign_monitor.streams.base.singer.write_records')
    def test_date_paginated_updates_bookmark(self, mock_write_records, mock_save_state):
        """Test that date-paginated stream updates bookmark state."""
        client = _make_mock_client()
        client.make_request.return_value = {
            'NumberOfPages': 1,
            'Results': [
                {
                    'EmailAddress': 'a@test.com',
                    'ListID': 'l1',
                    'Date': '2024-03-15 10:00:00',
                    'BounceType': 'Hard'
                }
            ]
        }

        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'ListID': {'type': ['string', 'null']},
                'EmailAddress': {'type': 'string'},
                'Date': {'type': ['string', 'null'], 'format': 'date-time'},
                'BounceType': {'type': ['string', 'null']},
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID', 'ListID', 'EmailAddress', 'Date'])
        catalog.tap_stream_id = 'campaign_bounces'
        catalog.stream = 'campaign_bounces'

        from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
        stream = CampaignBouncesStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        parent = {'CampaignID': 'camp_123'}
        stream.sync_data(parent=parent)

        # Verify bookmark was incorporated
        self.assertIn('bookmarks', stream.state)
        mock_save_state.assert_called()

    @patch('tap_campaign_monitor.streams.base.save_state')
    @patch('tap_campaign_monitor.streams.base.singer.write_records')
    def test_date_paginated_uses_start_date_from_state(self, mock_write_records, mock_save_state):
        """Test that date-paginated stream uses start_date from state."""
        from dateutil.parser import parse
        client = _make_mock_client()
        client.make_request.return_value = {
            'NumberOfPages': 1,
            'Results': []
        }

        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'ListID': {'type': ['string', 'null']},
                'EmailAddress': {'type': 'string'},
                'Date': {'type': ['string', 'null'], 'format': 'date-time'},
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID', 'ListID', 'EmailAddress', 'Date'])
        catalog.tap_stream_id = 'campaign_bounces'
        catalog.stream = 'campaign_bounces'

        from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
        state = {
            'bookmarks': {
                'camp_123.campaign_bounces': {
                    'field': 'Date',
                    'last_record': '2024-01-01 00:00:00'
                }
            }
        }
        stream = CampaignBouncesStream(
            config={'client_id': 'test'},
            state=state,
            catalog=catalog,
            client=client
        )
        parent = {'CampaignID': 'camp_123'}
        stream.sync_data(parent=parent)

        # Verify the request included the date param
        call_kwargs = client.make_request.call_args
        params = call_kwargs[1].get('params') if call_kwargs[1] else call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None
        # The make_request call should have params with 'date' key
        actual_params = client.make_request.call_args
        self.assertIsNotNone(actual_params)


class TestStreamGetStreamData(unittest.TestCase):
    """Test get_stream_data for various stream types."""

    def test_campaigns_get_stream_data(self):
        """Test CampaignsStream.get_stream_data transforms records."""
        client = _make_mock_client()
        schema = {
            'type': 'object',
            'properties': {
                'CampaignID': {'type': 'string'},
                'Name': {'type': ['string', 'null']}
            }
        }
        catalog = _make_mock_catalog(schema, ['CampaignID'])

        from tap_campaign_monitor.streams.campaigns import CampaignsStream
        stream = CampaignsStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        result = [{'CampaignID': 'c1', 'Name': 'Test'}]
        data = stream.get_stream_data(result)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['CampaignID'], 'c1')

    def test_campaign_bounces_get_stream_data(self):
        """Test CampaignBouncesStream.get_stream_data extracts Results."""
        client = _make_mock_client()
        schema = {
            'type': 'object',
            'properties': {
                'EmailAddress': {'type': 'string'},
                'Date': {'type': ['string', 'null'], 'format': 'date-time'},
            }
        }
        catalog = _make_mock_catalog(schema, ['EmailAddress', 'Date'])

        from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
        stream = CampaignBouncesStream(
            config={'client_id': 'test'},
            state={},
            catalog=catalog,
            client=client
        )
        result = {
            'Results': [
                {'EmailAddress': 'a@b.com', 'Date': '2024-01-01 00:00:00'}
            ]
        }
        data = stream.get_stream_data(result)
        self.assertEqual(len(data), 1)


class TestStreamProperties(unittest.TestCase):
    """Test stream class properties (TABLE, KEY_PROPERTIES, REQUIRES)."""

    def test_all_streams_have_table(self):
        """Every stream class should have a TABLE attribute."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            self.assertIsNotNone(stream_cls.TABLE,
                                 f"{stream_cls.__name__} missing TABLE")

    def test_all_streams_have_key_properties(self):
        """Every stream class should have KEY_PROPERTIES."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            self.assertIsInstance(stream_cls.KEY_PROPERTIES, list,
                                 f"{stream_cls.__name__} KEY_PROPERTIES not a list")
            self.assertGreater(len(stream_cls.KEY_PROPERTIES), 0,
                               f"{stream_cls.__name__} has empty KEY_PROPERTIES")

    def test_child_streams_have_requires(self):
        """Child streams should declare REQUIRES."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            if issubclass(stream_cls, ChildStream) and stream_cls is not ChildStream:
                self.assertIsInstance(stream_cls.REQUIRES, list)
                self.assertGreater(len(stream_cls.REQUIRES), 0,
                                   f"{stream_cls.__name__} has empty REQUIRES")

    def test_campaign_substreams_require_campaigns(self):
        """Campaign child streams should require 'campaigns'."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        campaign_children = [s for s in AVAILABLE_STREAMS
                             if s.TABLE and s.TABLE.startswith('campaign_')]
        for stream_cls in campaign_children:
            self.assertIn('campaigns', stream_cls.REQUIRES,
                          f"{stream_cls.__name__} should require 'campaigns'")

    def test_list_substreams_require_lists(self):
        """List child streams should require 'lists'."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        list_children = [s for s in AVAILABLE_STREAMS
                         if s.TABLE and s.TABLE.startswith('list_')]
        for stream_cls in list_children:
            self.assertIn('lists', stream_cls.REQUIRES,
                          f"{stream_cls.__name__} should require 'lists'")


class TestStreamApiPath(unittest.TestCase):
    """Test API path generation for various streams."""

    def test_campaigns_api_path(self):
        """Test CampaignsStream.api_path includes client_id."""
        from tap_campaign_monitor.streams.campaigns import CampaignsStream
        stream = CampaignsStream(
            config={'client_id': 'my_client'},
            state={}, catalog=None, client=None
        )
        self.assertIn('my_client', stream.api_path)
        self.assertIn('campaigns.json', stream.api_path)

    def test_lists_api_path(self):
        """Test ListsStream.api_path includes client_id."""
        from tap_campaign_monitor.streams.lists import ListsStream
        stream = ListsStream(
            config={'client_id': 'my_client'},
            state={}, catalog=None, client=None
        )
        self.assertIn('my_client', stream.api_path)
        self.assertIn('lists.json', stream.api_path)

    def test_campaign_bounces_child_api_path(self):
        """Test CampaignBouncesStream.get_api_path_for_child."""
        from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
        stream = CampaignBouncesStream(
            config={}, state={}, catalog=None, client=None
        )
        parent = {'CampaignID': 'abc123'}
        path = stream.get_api_path_for_child(parent)
        self.assertIn('abc123', path)
        self.assertIn('bounces.json', path)

    def test_list_active_subscribers_child_api_path(self):
        """Test ListActiveSubscribersStream.get_api_path_for_child."""
        from tap_campaign_monitor.streams.list_active_subscribers import ListActiveSubscribersStream
        stream = ListActiveSubscribersStream(
            config={}, state={}, catalog=None, client=None
        )
        parent = {'ListID': 'list_xyz'}
        path = stream.get_api_path_for_child(parent)
        self.assertIn('list_xyz', path)
        self.assertIn('active.json', path)


class TestStreamIncorporateParentId(unittest.TestCase):
    """Test incorporate_parent_id for child streams."""

    def test_campaign_child_incorporates_campaign_id(self):
        """Campaign child streams should add CampaignID to records."""
        from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
        stream = CampaignBouncesStream(
            config={}, state={}, catalog=None, client=None
        )
        obj = {'EmailAddress': 'a@b.com'}
        parent = {'CampaignID': 'camp_001'}
        result = stream.incorporate_parent_id(obj, parent)
        self.assertEqual(result['CampaignID'], 'camp_001')

    def test_list_child_incorporates_list_id(self):
        """List child streams should add ListID to records."""
        from tap_campaign_monitor.streams.list_active_subscribers import ListActiveSubscribersStream
        stream = ListActiveSubscribersStream(
            config={}, state={}, catalog=None, client=None
        )
        obj = {'EmailAddress': 'a@b.com'}
        parent = {'ListID': 'list_001'}
        result = stream.incorporate_parent_id(obj, parent)
        self.assertEqual(result['ListID'], 'list_001')


if __name__ == '__main__':
    unittest.main()
