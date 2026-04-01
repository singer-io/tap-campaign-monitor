"""Integration test: pagination — verify multi-page responses are fully
consumed for PaginatedChildStream and DatePaginatedChildStream."""
import unittest
from unittest.mock import patch

from .base import CampaignMonitorMockBaseTest


class PaginationIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):
    """Test that paginated streams fetch all pages of results."""

    # ------------------------------------------------------------------
    # PaginatedChildStream (campaign_recipients)
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_paginated_child_stream_fetches_all_pages(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """campaign_recipients (PaginatedChildStream) should fetch
        records from all pages."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_recipients'])
        client = self._create_paginated_mock_client()
        self._run_sync(catalog, client=client)

        all_recipients = []
        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaign_recipients':
                all_recipients.extend(call_args[0][1])

        # Two pages with 1 record each
        self.assertEqual(len(all_recipients), 2)
        emails = {r['EmailAddress'] for r in all_recipients}
        self.assertIn('recipient1@example.com', emails)
        self.assertIn('recipient2@example.com', emails)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_paginated_child_all_records_have_parent_id(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """All paginated records should have CampaignID injected."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_recipients'])
        client = self._create_paginated_mock_client()
        self._run_sync(catalog, client=client)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaign_recipients':
                for record in call_args[0][1]:
                    self.assertIn('CampaignID', record)
                    self.assertEqual(record['CampaignID'], 'camp-001')

    # ------------------------------------------------------------------
    # DatePaginatedChildStream (campaign_bounces)
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_date_paginated_child_stream_fetches_all_pages(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """campaign_bounces (DatePaginatedChildStream) should fetch
        records from all pages."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        client = self._create_paginated_mock_client()
        self._run_sync(catalog, client=client)

        all_bounces = []
        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaign_bounces':
                all_bounces.extend(call_args[0][1])

        self.assertEqual(len(all_bounces), 2)
        emails = {r['EmailAddress'] for r in all_bounces}
        self.assertIn('bounce1@example.com', emails)
        self.assertIn('bounce2@example.com', emails)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_date_paginated_child_state_updated_across_pages(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Bookmark state should reflect the latest record across all pages."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        client = self._create_paginated_mock_client()
        state = self._run_sync(catalog, client=client)

        bookmarks = state.get('bookmarks', {})
        bm = bookmarks.get('camp-001.campaign_bounces', {})
        self.assertEqual(bm.get('field'), 'Date')
        # Last record from page 2: "2024-06-17 09:00:00"
        self.assertIn('2024-06-17', bm.get('last_record', ''))

    # ------------------------------------------------------------------
    # DatePaginatedChildStream (list_active_subscribers)
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_subscriber_pagination(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """list_active_subscribers (DatePaginatedChildStream) should
        fetch records from all pages."""
        catalog = self._make_selected_catalog(
            stream_names=['lists', 'list_active_subscribers'])
        client = self._create_paginated_mock_client()
        self._run_sync(catalog, client=client)

        all_subs = []
        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'list_active_subscribers':
                all_subs.extend(call_args[0][1])

        self.assertEqual(len(all_subs), 2)
        emails = {r['EmailAddress'] for r in all_subs}
        self.assertIn('active1@example.com', emails)
        self.assertIn('active2@example.com', emails)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_subscriber_pagination_state(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """list_active_subscribers bookmark reflects last record across pages."""
        catalog = self._make_selected_catalog(
            stream_names=['lists', 'list_active_subscribers'])
        client = self._create_paginated_mock_client()
        state = self._run_sync(catalog, client=client)

        bookmarks = state.get('bookmarks', {})
        bm = bookmarks.get('list-001.list_active_subscribers', {})
        self.assertEqual(bm.get('field'), 'Date')
        # Last record from page 2: "2024-02-20 11:00:00"
        self.assertIn('2024-02-20', bm.get('last_record', ''))

    # ------------------------------------------------------------------
    # Single-page streams still work with paginated client
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_non_paginated_streams_unaffected(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Non-paginated streams (campaign_summary, list_details) still
        produce correct results when using paginated mock client."""
        catalog = self._make_selected_catalog(
            stream_names=[
                'campaigns', 'campaign_summary',
                'lists', 'list_details',
            ])
        client = self._create_paginated_mock_client()
        self._run_sync(catalog, client=client)

        written = {c[0][0] for c in mock_write_records.call_args_list}
        self.assertIn('campaign_summary', written)
        self.assertIn('list_details', written)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_paginated_make_request_called_multiple_times(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """For a 2-page stream, make_request should be called at least twice
        for the paginated endpoint."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_recipients'])
        client = self._create_paginated_mock_client()
        self._run_sync(catalog, client=client)

        recipient_calls = [
            c for c in client.make_request.call_args_list
            if '/recipients.json' in str(c)
        ]
        self.assertGreaterEqual(len(recipient_calls), 2)
