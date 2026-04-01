"""Integration test: with only automatic (primary-key) fields selected,
verify those fields still appear in every replicated record."""
import unittest
from unittest.mock import patch

from .base import CampaignMonitorMockBaseTest


class AutomaticFieldsIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):
    """Test that with no fields selected for a stream, automatic fields
    (primary keys) are still replicated."""

    STREAMS_TO_EXCLUDE = {
        # Campaign event streams: require parent + real interactions
        # We still test them when parent is selected
    }

    def _streams_with_parent(self):
        """All streams grouped with required parents."""
        return {
            'campaigns': ['campaigns'],
            'campaign_bounces': ['campaigns', 'campaign_bounces'],
            'campaign_clicks': ['campaigns', 'campaign_clicks'],
            'campaign_email_client_usage': ['campaigns', 'campaign_email_client_usage'],
            'campaign_opens': ['campaigns', 'campaign_opens'],
            'campaign_recipients': ['campaigns', 'campaign_recipients'],
            'campaign_spam_complaints': ['campaigns', 'campaign_spam_complaints'],
            'campaign_summary': ['campaigns', 'campaign_summary'],
            'campaign_unsubscribes': ['campaigns', 'campaign_unsubscribes'],
            'lists': ['lists'],
            'list_active_subscribers': ['lists', 'list_active_subscribers'],
            'list_bounced_subscribers': ['lists', 'list_bounced_subscribers'],
            'list_deleted_subscribers': ['lists', 'list_deleted_subscribers'],
            'list_details': ['lists', 'list_details'],
            'list_unconfirmed_subscribers': ['lists', 'list_unconfirmed_subscribers'],
            'list_unsubscribed_subscribers': ['lists', 'list_unsubscribed_subscribers'],
        }

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_automatic_fields_present_for_all_streams(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """When only automatic fields are selected, every record still
        contains the primary key fields for its stream."""
        catalog = self._make_automatic_fields_catalog()
        self._run_sync(catalog)

        expected = self.expected_metadata()
        written = {}
        for call_args in mock_write_records.call_args_list:
            stream_name = call_args[0][0]
            records = call_args[0][1]
            written.setdefault(stream_name, []).extend(records)

        for stream_name, records in written.items():
            pk_fields = expected[stream_name][self.PRIMARY_KEYS]
            for record in records:
                for pk in pk_fields:
                    self.assertIn(
                        pk, record,
                        f"Primary key '{pk}' missing in {stream_name} record",
                    )

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_automatic_fields_campaigns_only(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Automatic fields test for campaigns stream only."""
        catalog = self._make_automatic_fields_catalog(
            stream_names=['campaigns'])
        self._run_sync(catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaigns':
                for record in call_args[0][1]:
                    self.assertIn('CampaignID', record)
                return
        self.fail("No campaigns records written")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_automatic_fields_lists_only(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Automatic fields test for lists stream only."""
        catalog = self._make_automatic_fields_catalog(
            stream_names=['lists'])
        self._run_sync(catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'lists':
                for record in call_args[0][1]:
                    self.assertIn('ListID', record)
                return
        self.fail("No lists records written")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_automatic_fields_campaign_child_streams(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Campaign child streams have their primary keys when only
        automatic fields are selected."""
        child_streams = [
            'campaign_bounces', 'campaign_clicks', 'campaign_opens',
            'campaign_recipients', 'campaign_spam_complaints',
            'campaign_unsubscribes', 'campaign_summary',
            'campaign_email_client_usage',
        ]
        catalog = self._make_automatic_fields_catalog(
            stream_names=['campaigns'] + child_streams)
        self._run_sync(catalog)

        expected = self.expected_metadata()
        written = {}
        for call_args in mock_write_records.call_args_list:
            stream_name = call_args[0][0]
            written.setdefault(stream_name, []).extend(call_args[0][1])

        for stream_name in child_streams:
            self.assertIn(stream_name, written,
                          f"No records for {stream_name}")
            pk_fields = expected[stream_name][self.PRIMARY_KEYS]
            for record in written[stream_name]:
                for pk in pk_fields:
                    self.assertIn(pk, record,
                                  f"PK '{pk}' missing in {stream_name}")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_automatic_fields_list_child_streams(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """List child streams have their primary keys when only
        automatic fields are selected."""
        child_streams = [
            'list_details', 'list_active_subscribers',
            'list_bounced_subscribers', 'list_deleted_subscribers',
            'list_unconfirmed_subscribers', 'list_unsubscribed_subscribers',
        ]
        catalog = self._make_automatic_fields_catalog(
            stream_names=['lists'] + child_streams)
        self._run_sync(catalog)

        expected = self.expected_metadata()
        written = {}
        for call_args in mock_write_records.call_args_list:
            stream_name = call_args[0][0]
            written.setdefault(stream_name, []).extend(call_args[0][1])

        for stream_name in child_streams:
            self.assertIn(stream_name, written,
                          f"No records for {stream_name}")
            pk_fields = expected[stream_name][self.PRIMARY_KEYS]
            for record in written[stream_name]:
                for pk in pk_fields:
                    self.assertIn(pk, record,
                                  f"PK '{pk}' missing in {stream_name}")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_schema_emitted_with_automatic_fields_only(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Schemas are still emitted even when only automatic fields selected."""
        catalog = self._make_automatic_fields_catalog()
        self._run_sync(catalog)

        schema_streams = {c[0][0] for c in mock_write_schema.call_args_list}
        self.assertIn('campaigns', schema_streams)
        self.assertIn('lists', schema_streams)
