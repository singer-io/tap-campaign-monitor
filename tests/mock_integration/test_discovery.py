"""Integration test: discovery produces correct catalog and metadata."""
import unittest

from tap_campaign_monitor.client import CampaignMonitorForbiddenError
from tap_campaign_monitor.discover import discover

from .base import CampaignMonitorMockBaseTest


class DiscoveryIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):

    def test_discovery_returns_all_expected_streams(self):
        """Verify discover returns all expected streams."""
        catalog_entries = self._run_discover()
        stream_ids = {e['tap_stream_id'] for e in catalog_entries}
        self.assertEqual(stream_ids, self.ALL_STREAM_IDS)

    def test_discovery_key_properties_match_expected(self):
        """Verify each stream has the expected primary keys."""
        catalog_entries = self._run_discover()
        expected = self.expected_metadata()
        for entry in catalog_entries:
            with self.subTest(stream=entry['tap_stream_id']):
                actual_keys = set(entry['key_properties'])
                self.assertEqual(
                    actual_keys,
                    expected[entry['tap_stream_id']][self.PRIMARY_KEYS],
                )

    def test_discovery_schema_properties_exist(self):
        """Each stream schema has at least one property."""
        catalog_entries = self._run_discover()
        for entry in catalog_entries:
            with self.subTest(stream=entry['tap_stream_id']):
                schema = entry['schema']
                self.assertIn('properties', schema)
                self.assertTrue(len(schema['properties']) > 0)

    def test_discovery_key_properties_in_schema(self):
        """Key properties listed in metadata exist in the schema."""
        catalog_entries = self._run_discover()
        for entry in catalog_entries:
            with self.subTest(stream=entry['tap_stream_id']):
                schema_props = set(entry['schema'].get('properties', {}).keys())
                key_props = set(entry['key_properties'])
                self.assertTrue(
                    key_props.issubset(schema_props),
                    f"key_properties {key_props} not in schema {schema_props}",
                )

    def test_discovery_metadata_inclusion(self):
        """Key properties have automatic inclusion, others available."""
        catalog_entries = self._run_discover()
        expected = self.expected_metadata()
        for entry in catalog_entries:
            with self.subTest(stream=entry['tap_stream_id']):
                mdata = {tuple(m['breadcrumb']): m['metadata']
                         for m in entry['metadata']}
                pk_names = expected[entry['tap_stream_id']][self.PRIMARY_KEYS]
                for field_name in entry['schema'].get('properties', {}):
                    breadcrumb = ('properties', field_name)
                    if breadcrumb in mdata:
                        if field_name in pk_names:
                            self.assertEqual(
                                mdata[breadcrumb].get('inclusion'),
                                'automatic',
                                f"{field_name} should be automatic",
                            )
                        else:
                            self.assertEqual(
                                mdata[breadcrumb].get('inclusion'),
                                'available',
                                f"{field_name} should be available",
                            )


class DiscoveryExclusionIntegrationTest(CampaignMonitorMockBaseTest, unittest.TestCase):
    """Integration tests: unauthorized streams are excluded from catalog."""

    def _run_discover_with_client(self, client):
        return discover(self.default_config, {}, client)

    def test_all_streams_present_when_all_accessible(self):
        """Full catalog returned when no streams are blocked."""
        client = self._create_mock_client()
        entries = self._run_discover_with_client(client)
        stream_ids = {e['tap_stream_id'] for e in entries}
        self.assertEqual(stream_ids, self.ALL_STREAM_IDS)

    def test_campaigns_and_children_excluded_when_403(self):
        """campaigns + campaign_* excluded when campaigns returns 403."""
        client = self._create_forbidden_mock_client(blocked_streams={'campaigns'})
        entries = self._run_discover_with_client(client)
        stream_ids = {e['tap_stream_id'] for e in entries}
        campaign_streams = {s for s in self.ALL_STREAM_IDS
                            if s == 'campaigns' or s.startswith('campaign_')}
        self.assertTrue(campaign_streams.isdisjoint(stream_ids),
                        f"Unexpected campaign streams in catalog: {campaign_streams & stream_ids}")
        lists_streams = {s for s in self.ALL_STREAM_IDS
                         if s == 'lists' or s.startswith('list_')}
        self.assertTrue(lists_streams.issubset(stream_ids))

    def test_lists_and_children_excluded_when_403(self):
        """lists + list_* excluded when lists returns 403."""
        client = self._create_forbidden_mock_client(blocked_streams={'lists'})
        entries = self._run_discover_with_client(client)
        stream_ids = {e['tap_stream_id'] for e in entries}
        list_streams = {s for s in self.ALL_STREAM_IDS
                        if s == 'lists' or s.startswith('list_')}
        self.assertTrue(list_streams.isdisjoint(stream_ids),
                        f"Unexpected list streams in catalog: {list_streams & stream_ids}")
        campaign_streams = {s for s in self.ALL_STREAM_IDS
                            if s == 'campaigns' or s.startswith('campaign_')}
        self.assertTrue(campaign_streams.issubset(stream_ids))

    def test_all_parents_blocked_raises_forbidden_error(self):
        """CampaignMonitorForbiddenError raised when all parents blocked."""
        client = self._create_forbidden_mock_client(
            blocked_streams={'campaigns', 'lists'})
        with self.assertRaises(CampaignMonitorForbiddenError):
            self._run_discover_with_client(client)
