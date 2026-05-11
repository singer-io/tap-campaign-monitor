"""Integration test: sync all streams with mocked API responses
and verify all fields are replicated."""
import unittest
from unittest.mock import patch

from .base import CampaignMonitorMockBaseTest


class AllFieldsIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):

    def setUp(self):
        self.catalog = self._make_selected_catalog()

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_sync_writes_records_for_all_streams(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Sync all streams and verify records are written for
        streams that have mock data."""
        self._run_sync(self.catalog)

        written_streams = {
            call_args[0][0] for call_args in mock_write_records.call_args_list
        }

        # Parent streams
        self.assertIn('campaigns', written_streams)
        self.assertIn('lists', written_streams)

        # Campaign child streams
        self.assertIn('campaign_summary', written_streams)
        self.assertIn('campaign_bounces', written_streams)
        self.assertIn('campaign_clicks', written_streams)
        self.assertIn('campaign_opens', written_streams)
        self.assertIn('campaign_recipients', written_streams)
        self.assertIn('campaign_spam_complaints', written_streams)
        self.assertIn('campaign_unsubscribes', written_streams)
        self.assertIn('campaign_email_client_usage', written_streams)

        # List child streams
        self.assertIn('list_details', written_streams)
        self.assertIn('list_active_subscribers', written_streams)
        self.assertIn('list_bounced_subscribers', written_streams)
        self.assertIn('list_deleted_subscribers', written_streams)
        self.assertIn('list_unconfirmed_subscribers', written_streams)
        self.assertIn('list_unsubscribed_subscribers', written_streams)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_campaign_records_have_campaign_id(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Campaign records have the CampaignID field."""
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaigns':
                for record in call_args[0][1]:
                    self.assertIn('CampaignID', record)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_records_have_list_id(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """List records have the ListID field."""
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'lists':
                for record in call_args[0][1]:
                    self.assertIn('ListID', record)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_campaign_child_records_have_campaign_id(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Campaign child stream records have CampaignID injected."""
        campaign_child_streams = {
            'campaign_summary', 'campaign_bounces', 'campaign_clicks',
            'campaign_opens', 'campaign_recipients',
            'campaign_spam_complaints', 'campaign_unsubscribes',
            'campaign_email_client_usage',
        }
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            stream_name = call_args[0][0]
            if stream_name in campaign_child_streams:
                for record in call_args[0][1]:
                    self.assertIn(
                        'CampaignID', record,
                        f"CampaignID missing in {stream_name} record",
                    )

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_child_records_have_list_id(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """List child stream records have ListID injected."""
        list_child_streams = {
            'list_details', 'list_active_subscribers',
            'list_bounced_subscribers', 'list_deleted_subscribers',
            'list_unconfirmed_subscribers', 'list_unsubscribed_subscribers',
        }
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            stream_name = call_args[0][0]
            if stream_name in list_child_streams:
                for record in call_args[0][1]:
                    self.assertIn(
                        'ListID', record,
                        f"ListID missing in {stream_name} record",
                    )

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_subscriber_records_have_email_address(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Subscriber child stream records have EmailAddress."""
        subscriber_streams = {
            'list_active_subscribers', 'list_bounced_subscribers',
            'list_deleted_subscribers', 'list_unconfirmed_subscribers',
            'list_unsubscribed_subscribers',
        }
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            stream_name = call_args[0][0]
            if stream_name in subscriber_streams:
                for record in call_args[0][1]:
                    self.assertIn(
                        'EmailAddress', record,
                        f"EmailAddress missing in {stream_name} record",
                    )

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_sync_only_campaigns(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Sync only campaigns and verify only campaign records are written."""
        catalog = self._make_selected_catalog(stream_names=['campaigns'])
        self._run_sync(catalog)

        written_streams = {
            call_args[0][0] for call_args in mock_write_records.call_args_list
        }
        self.assertIn('campaigns', written_streams)
        # No child streams should be synced
        self.assertNotIn('campaign_summary', written_streams)
        self.assertNotIn('lists', written_streams)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_sync_only_lists(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Sync only lists and verify only list records are written."""
        catalog = self._make_selected_catalog(stream_names=['lists'])
        self._run_sync(catalog)

        written_streams = {
            call_args[0][0] for call_args in mock_write_records.call_args_list
        }
        self.assertIn('lists', written_streams)
        self.assertNotIn('campaigns', written_streams)
        self.assertNotIn('list_details', written_streams)
