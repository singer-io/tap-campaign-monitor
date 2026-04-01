"""Integration test: bookmark / state management for DatePaginatedChildStreams."""
import unittest
from unittest.mock import patch

from .base import CampaignMonitorMockBaseTest


class BookmarkIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_date_paginated_child_stream_updates_state(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """DatePaginatedChildStreams (e.g. campaign_bounces) should
        update state bookmarks with Date values."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        state = self._run_sync(catalog)

        bookmarks = state.get('bookmarks', {})
        expected_key = self.get_bookmark_key('campaigns', 'campaign_bounces')
        self.assertIn(expected_key, bookmarks)
        bookmark = bookmarks[expected_key]
        self.assertEqual(bookmark.get('field'), 'Date')
        self.assertIsNotNone(bookmark.get('last_record'))

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_full_table_parent_does_not_write_bookmarks(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Parent streams (campaigns, lists) are FULL_TABLE and should
        not write bookmark entries."""
        catalog = self._make_selected_catalog(stream_names=['campaigns'])
        state = self._run_sync(catalog)

        bookmarks = state.get('bookmarks', {})
        self.assertNotIn('campaigns', bookmarks)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_subscriber_stream_updates_state(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """List subscriber DatePaginatedChildStreams should update state."""
        catalog = self._make_selected_catalog(
            stream_names=['lists', 'list_active_subscribers'])
        state = self._run_sync(catalog)

        bookmarks = state.get('bookmarks', {})
        expected_key = self.get_bookmark_key('lists', 'list_active_subscribers')
        self.assertIn(expected_key, bookmarks)
        bookmark = bookmarks[expected_key]
        self.assertEqual(bookmark.get('field'), 'Date')
        self.assertIsNotNone(bookmark.get('last_record'))

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_state_written_during_sync(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """write_state is called during sync to persist progress."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        self._run_sync(catalog)
        self.assertTrue(mock_write_state.called)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_multiple_date_paginated_streams_each_get_bookmarks(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Multiple DatePaginatedChildStreams get their own bookmarks."""
        catalog = self._make_selected_catalog(
            stream_names=[
                'campaigns', 'campaign_bounces', 'campaign_clicks',
                'campaign_opens',
            ])
        state = self._run_sync(catalog)

        bookmarks = state.get('bookmarks', {})
        self.assertIn(
            self.get_bookmark_key('campaigns', 'campaign_bounces'), bookmarks)
        self.assertIn(
            self.get_bookmark_key('campaigns', 'campaign_clicks'), bookmarks)
        self.assertIn(
            self.get_bookmark_key('campaigns', 'campaign_opens'), bookmarks)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_bookmark_structure_has_field_and_last_record(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Bookmark entries should have 'field' and 'last_record' keys."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_bounces'])
        state = self._run_sync(catalog)

        bookmarks = state.get('bookmarks', {})
        key = self.get_bookmark_key('campaigns', 'campaign_bounces')
        bm = bookmarks.get(key, {})
        self.assertIn('field', bm)
        self.assertIn('last_record', bm)
        self.assertEqual(bm['field'], 'Date')
        self.assertIsInstance(bm['last_record'], str)
