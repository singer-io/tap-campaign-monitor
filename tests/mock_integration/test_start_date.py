"""Integration test: start-date / bookmark resume — verify that
DatePaginatedChildStream passes the bookmark date to the API and that
a second sync with prior state picks up where it left off."""
import unittest
from unittest.mock import patch

from .base import CampaignMonitorMockBaseTest


class StartDateIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):
    """Test that bookmarked state is used as a start_date on subsequent syncs."""

    # ------------------------------------------------------------------
    # First sync: no initial state → no date param sent
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_first_sync_no_date_param(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """On first sync (no state), the date param should NOT be sent
        to date-paginated endpoints."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        client = self._create_mock_client()
        self._run_sync(catalog, state={}, client=client)

        # Find the bounces API call and check params
        for call_args in client.make_request.call_args_list:
            url = call_args[0][0]
            if '/bounces.json' in url:
                params = call_args[1].get('params') or (
                    call_args[0][2] if len(call_args[0]) > 2 else None)
                if params:
                    self.assertNotIn('date', params,
                                     "date param should not be set on first sync")
                return

    # ------------------------------------------------------------------
    # Second sync: prior bookmark → date param sent
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_second_sync_uses_bookmark_as_date_param(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """On second sync with existing bookmark, the date param should
        be sent to the API."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        initial_state = {
            'bookmarks': {
                'camp-001.campaign_bounces': {
                    'field': 'Date',
                    'last_record': '2024-06-16 08:00:00',
                }
            }
        }
        client = self._create_date_filtering_mock_client()
        self._run_sync(catalog, state=initial_state, client=client)

        # Find the bounces API call
        for call_args in client.make_request.call_args_list:
            url = call_args[0][0]
            if '/bounces.json' in url:
                params = call_args[1].get('params') or (
                    call_args[0][2] if len(call_args[0]) > 2 else None)
                if params:
                    self.assertIn('date', params,
                                  "date param should be set on second sync")
                    return

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_second_sync_returns_only_recent_records(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """When bookmark state exists, the API returns only records after
        the bookmark date."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        initial_state = {
            'bookmarks': {
                'camp-001.campaign_bounces': {
                    'field': 'Date',
                    'last_record': '2024-06-16 08:00:00',
                }
            }
        }
        client = self._create_date_filtering_mock_client()
        self._run_sync(catalog, state=initial_state, client=client)

        bounced_records = []
        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaign_bounces':
                bounced_records.extend(call_args[0][1])

        # With date filter, mock returns MOCK_CAMPAIGN_BOUNCES_RECENT (1 record)
        self.assertEqual(len(bounced_records), 1)
        self.assertEqual(
            bounced_records[0]['EmailAddress'], 'recent-bounce@example.com')

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_bookmark_updated_after_second_sync(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Bookmark should be updated to the latest record date after
        the second sync."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        initial_state = {
            'bookmarks': {
                'camp-001.campaign_bounces': {
                    'field': 'Date',
                    'last_record': '2024-06-16 08:00:00',
                }
            }
        }
        client = self._create_date_filtering_mock_client()
        state = self._run_sync(catalog, state=initial_state, client=client)

        bookmarks = state.get('bookmarks', {})
        bm = bookmarks.get('camp-001.campaign_bounces', {})
        # MOCK_CAMPAIGN_BOUNCES_RECENT has Date "2024-07-01 10:00:00"
        self.assertIn('2024-07-01', bm.get('last_record', ''))

    # ------------------------------------------------------------------
    # Full-table parent streams ignore start_date
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_parent_streams_always_return_all_records(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Parent streams (campaigns, lists) are FULL_TABLE and always
        return all records regardless of state."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'lists'])
        initial_state = {
            'bookmarks': {
                'some_other_key': {
                    'field': 'Date',
                    'last_record': '2025-01-01 00:00:00',
                }
            }
        }
        self._run_sync(catalog, state=initial_state)

        campaigns_records = []
        lists_records = []
        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaigns':
                campaigns_records.extend(call_args[0][1])
            elif call_args[0][0] == 'lists':
                lists_records.extend(call_args[0][1])

        self.assertEqual(len(campaigns_records), len(self.MOCK_CAMPAIGNS))
        self.assertEqual(len(lists_records), len(self.MOCK_LISTS))

    # ------------------------------------------------------------------
    # List subscriber start_date
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_subscriber_second_sync_uses_bookmark(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """list_active_subscribers uses bookmark on second sync."""
        catalog = self._make_selected_catalog(
            stream_names=['lists', 'list_active_subscribers'])
        initial_state = {
            'bookmarks': {
                'list-001.list_active_subscribers': {
                    'field': 'Date',
                    'last_record': '2024-01-01 00:00:00',
                }
            }
        }
        client = self._create_date_filtering_mock_client()
        self._run_sync(catalog, state=initial_state, client=client)

        # Verify date param was sent
        for call_args in client.make_request.call_args_list:
            url = call_args[0][0]
            if '/active.json' in url:
                params = call_args[1].get('params') or (
                    call_args[0][2] if len(call_args[0]) > 2 else None)
                if params:
                    self.assertIn('date', params,
                                  "date param should be set for subscriber "
                                  "stream with existing bookmark")
                    return

    # ------------------------------------------------------------------
    # Two consecutive syncs: end-to-end
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_two_consecutive_syncs_produce_state(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Running two syncs: first populates state, second uses it."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])

        # First sync — no initial state
        state1 = self._run_sync(catalog, state={})
        self.assertIn('bookmarks', state1)
        self.assertIn('camp-001.campaign_bounces', state1['bookmarks'])

        # Second sync — re-uses state from first
        mock_write_records.reset_mock()
        client2 = self._create_date_filtering_mock_client()
        state2 = self._run_sync(catalog, state=state1, client=client2)

        # State still has bookmarks after second sync
        self.assertIn('camp-001.campaign_bounces', state2['bookmarks'])
        bm = state2['bookmarks']['camp-001.campaign_bounces']
        self.assertEqual(bm['field'], 'Date')
        self.assertIsNotNone(bm['last_record'])
