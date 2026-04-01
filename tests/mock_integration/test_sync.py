"""Integration test: do_sync() end-to-end pipeline writes schemas,
records, and state correctly."""
import unittest
from unittest.mock import patch

from .base import CampaignMonitorMockBaseTest


class DoSyncIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):

    def setUp(self):
        self.catalog = self._make_selected_catalog()

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_full_pipeline_emits_schemas_and_records(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """sync should emit SCHEMA then RECORD for each synced stream."""
        self._run_sync(self.catalog)

        schema_streams = {c[0][0] for c in mock_write_schema.call_args_list}
        record_streams = {c[0][0] for c in mock_write_records.call_args_list}

        self.assertIn('campaigns', schema_streams)
        self.assertIn('campaigns', record_streams)
        self.assertIn('lists', schema_streams)
        self.assertIn('lists', record_streams)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_correct_record_counts_for_campaigns(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """sync emits the right number of records for campaigns."""
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaigns':
                records = call_args[0][1]
                self.assertEqual(len(records), len(self.MOCK_CAMPAIGNS))
                return
        self.fail("No campaigns records written")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_correct_record_counts_for_lists(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """sync emits the right number of records for lists."""
        self._run_sync(self.catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'lists':
                records = call_args[0][1]
                self.assertEqual(len(records), len(self.MOCK_LISTS))
                return
        self.fail("No lists records written")

    # ------------------------------------------------------------------
    # Schema emission order
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_schema_emitted_before_records(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """For each stream, write_schema must be called before write_records."""
        call_order = []
        mock_write_schema.side_effect = lambda *a, **k: call_order.append(('schema', a[0]))
        mock_write_records.side_effect = lambda *a, **k: call_order.append(('record', a[0]))

        self._run_sync(self.catalog)

        for stream_name in ('campaigns', 'lists'):
            schema_indices = [
                i for i, (t, s) in enumerate(call_order)
                if t == 'schema' and s == stream_name
            ]
            record_indices = [
                i for i, (t, s) in enumerate(call_order)
                if t == 'record' and s == stream_name
            ]
            if schema_indices and record_indices:
                self.assertLess(
                    schema_indices[0], record_indices[0],
                    f"Schema for {stream_name} must come before its records",
                )

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_schema_includes_key_properties(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """write_schema is called with correct key_properties for each stream."""
        self._run_sync(self.catalog)

        expected = self.expected_metadata()
        for schema_call in mock_write_schema.call_args_list:
            stream_name = schema_call[0][0]
            if stream_name in expected:
                # singer.write_schema(stream_name, schema_dict, key_properties)
                key_props = schema_call[1].get('key_properties', schema_call[0][2]
                                                if len(schema_call[0]) > 2 else None)
                if key_props is not None:
                    self.assertEqual(
                        set(key_props),
                        expected[stream_name][self.PRIMARY_KEYS],
                        f"key_properties mismatch for {stream_name}",
                    )

    # ------------------------------------------------------------------
    # Stream selection
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_only_selected_streams_are_synced(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """When only 'campaigns' is selected, other streams are skipped."""
        catalog = self._make_selected_catalog(stream_names=['campaigns'])
        self._run_sync(catalog)

        record_streams = {c[0][0] for c in mock_write_records.call_args_list}
        self.assertIn('campaigns', record_streams)
        self.assertNotIn('lists', record_streams)
        self.assertNotIn('campaign_summary', record_streams)

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_no_streams_selected_writes_nothing(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """When no streams are selected, nothing is written."""
        catalog = self._make_selected_catalog(stream_names=[])
        self._run_sync(catalog)

        mock_write_records.assert_not_called()

    # ------------------------------------------------------------------
    # Record field correctness
    # ------------------------------------------------------------------

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_campaign_records_have_correct_types(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Campaign records have properly typed fields."""
        catalog = self._make_selected_catalog(stream_names=['campaigns'])
        self._run_sync(catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaigns':
                record = call_args[0][1][0]
                self.assertIsInstance(record['CampaignID'], str)
                self.assertIsInstance(record['Name'], str)
                return
        self.fail("No campaigns records written")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_campaign_summary_record_has_expected_fields(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """Campaign summary records have expected numeric fields."""
        catalog = self._make_selected_catalog(
            stream_names=['campaigns', 'campaign_summary'])
        self._run_sync(catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'campaign_summary':
                record = call_args[0][1][0]
                self.assertIn('CampaignID', record)
                self.assertIn('Recipients', record)
                self.assertIn('TotalOpened', record)
                self.assertIn('Clicks', record)
                return
        self.fail("No campaign_summary records written")

    @patch("singer.write_state")
    @patch("singer.write_records")
    @patch("singer.write_schema")
    def test_list_details_record_has_expected_fields(
        self, mock_write_schema, mock_write_records, mock_write_state,
    ):
        """List details records have expected fields."""
        catalog = self._make_selected_catalog(
            stream_names=['lists', 'list_details'])
        self._run_sync(catalog)

        for call_args in mock_write_records.call_args_list:
            if call_args[0][0] == 'list_details':
                record = call_args[0][1][0]
                self.assertIn('ListID', record)
                self.assertIn('Title', record)
                return
        self.fail("No list_details records written")

    # ------------------------------------------------------------------
    # Parent-child relationship
    # ------------------------------------------------------------------

    def test_campaign_child_requires_campaigns_selected(
        self,
    ):
        """Campaign child streams require 'campaigns' to be selected.
        Selecting a child without its parent raises RuntimeError."""
        catalog = self._make_selected_catalog(
            stream_names=['campaign_summary'])
        with self.assertRaises(RuntimeError):
            self._run_sync(catalog)

    def test_list_child_requires_lists_selected(
        self,
    ):
        """List child streams require 'lists' to be selected."""
        catalog = self._make_selected_catalog(
            stream_names=['list_details'])
        with self.assertRaises(RuntimeError):
            self._run_sync(catalog)
