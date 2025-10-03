import unittest
from unittest.mock import Mock

from tap_campaign_monitor.streams.base import BaseStream, ChildStream
from tap_campaign_monitor.streams.campaigns import CampaignsStream
from tap_campaign_monitor.streams.lists import ListsStream
from tap_campaign_monitor.streams.campaign_opens import CampaignOpensStream
from tap_campaign_monitor.streams.campaign_summary import CampaignSummaryStream
from tap_campaign_monitor.streams.list_details import ListDetailsStream
from tap_campaign_monitor.streams.list_active_subscribers import ListActiveSubscribersStream
from tap_campaign_monitor.streams import AVAILABLE_STREAMS


class TestCatalogProperties(unittest.TestCase):

    def setUp(self):
        self.config = {"client_id": "test_client"}
        self.state = {}
        self.catalog = None
        self.client = Mock()

    def test_base_stream_default_properties(self):
        """Test that BaseStream has the expected default properties."""
        # Test default class attributes
        self.assertEqual(BaseStream.KEY_PROPERTIES, ['id'])
        self.assertEqual(BaseStream.API_METHOD, 'GET')
        self.assertEqual(BaseStream.TABLE, None)
        self.assertEqual(BaseStream.REQUIRES, [])
        self.assertEqual(BaseStream.REPLICATION_METHOD, 'FULL_TABLE')
        self.assertEqual(BaseStream.REPLICATION_KEYS, [])
        self.assertEqual(BaseStream.PARENT, '')

    def test_campaigns_stream_key_properties(self):
        """Test that CampaignsStream has correct KEY_PROPERTIES."""
        stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(stream.KEY_PROPERTIES, ['CampaignID'])
        self.assertEqual(stream.TABLE, 'campaigns')

    def test_lists_stream_key_properties(self):
        """Test that ListsStream has correct KEY_PROPERTIES."""
        stream = ListsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(stream.KEY_PROPERTIES, ['ListID'])
        self.assertEqual(stream.TABLE, 'lists')

    def test_campaign_opens_stream_key_properties(self):
        """Test that CampaignOpensStream has correct KEY_PROPERTIES."""
        stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(stream.KEY_PROPERTIES, ['CampaignID', 'ListID', 'EmailAddress', 'Date'])
        self.assertEqual(stream.TABLE, 'campaign_opens')

    def test_campaign_summary_stream_key_properties(self):
        """Test that CampaignSummaryStream has correct KEY_PROPERTIES."""
        stream = CampaignSummaryStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(stream.KEY_PROPERTIES, ['CampaignID'])
        self.assertEqual(stream.TABLE, 'campaign_summary')

    def test_list_details_stream_key_properties(self):
        """Test that ListDetailsStream has correct KEY_PROPERTIES."""
        stream = ListDetailsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(stream.KEY_PROPERTIES, ['ListID'])
        self.assertEqual(stream.TABLE, 'list_details')

    def test_list_active_subscribers_stream_key_properties(self):
        """Test that ListActiveSubscribersStream has correct KEY_PROPERTIES."""
        stream = ListActiveSubscribersStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(stream.KEY_PROPERTIES, ['ListID', 'EmailAddress', 'Date'])
        self.assertEqual(stream.TABLE, 'list_active_subscribers')

    def test_all_streams_have_key_properties(self):
        """Test that all available streams have KEY_PROPERTIES defined."""
        for stream_class in AVAILABLE_STREAMS:
            with self.subTest(stream_class=stream_class.__name__):
                stream = stream_class(self.config, self.state, self.catalog, self.client)
                self.assertIsNotNone(stream.KEY_PROPERTIES)
                self.assertIsInstance(stream.KEY_PROPERTIES, list)
                self.assertGreater(len(stream.KEY_PROPERTIES), 0)

    def test_replication_method_defaults(self):
        """Test that streams have correct REPLICATION_METHOD."""
        # Test base streams use default FULL_TABLE
        campaigns_stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaigns_stream.REPLICATION_METHOD, 'FULL_TABLE')
        
        lists_stream = ListsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(lists_stream.REPLICATION_METHOD, 'FULL_TABLE')

        # Test child streams inherit FULL_TABLE
        campaign_opens_stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaign_opens_stream.REPLICATION_METHOD, 'FULL_TABLE')

        list_details_stream = ListDetailsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(list_details_stream.REPLICATION_METHOD, 'FULL_TABLE')

    def test_replication_keys_defaults(self):
        """Test that streams have correct REPLICATION_KEYS."""
        # Test base streams use default empty list
        campaigns_stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaigns_stream.REPLICATION_KEYS, [])
        
        lists_stream = ListsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(lists_stream.REPLICATION_KEYS, [])

        # Test child streams inherit empty list
        campaign_opens_stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaign_opens_stream.REPLICATION_KEYS, [])

        list_details_stream = ListDetailsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(list_details_stream.REPLICATION_KEYS, [])

    def test_all_streams_replication_properties(self):
        """Test that all available streams have correct replication properties."""
        for stream_class in AVAILABLE_STREAMS:
            with self.subTest(stream_class=stream_class.__name__):
                stream = stream_class(self.config, self.state, self.catalog, self.client)
                
                # All streams should have REPLICATION_METHOD
                self.assertIsNotNone(stream.REPLICATION_METHOD)
                self.assertIsInstance(stream.REPLICATION_METHOD, str)
                self.assertEqual(stream.REPLICATION_METHOD, 'FULL_TABLE')
                
                # All streams should have REPLICATION_KEYS as a list
                self.assertIsNotNone(stream.REPLICATION_KEYS)
                self.assertIsInstance(stream.REPLICATION_KEYS, list)
                self.assertEqual(stream.REPLICATION_KEYS, [])

    def test_parent_tap_stream_id_for_child_streams(self):
        """Test that child streams have correct PARENT attribute."""
        # Campaign child streams should have 'campaigns' as parent
        campaign_opens_stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaign_opens_stream.PARENT, 'campaigns')
        
        campaign_summary_stream = CampaignSummaryStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaign_summary_stream.PARENT, 'campaigns')

        # List child streams should have 'lists' as parent
        list_details_stream = ListDetailsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(list_details_stream.PARENT, 'lists')
        
        list_active_subscribers_stream = ListActiveSubscribersStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(list_active_subscribers_stream.PARENT, 'lists')

    def test_parent_tap_stream_id_for_base_streams(self):
        """Test that base streams have empty PARENT attribute."""
        campaigns_stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaigns_stream.PARENT, '')
        
        lists_stream = ListsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(lists_stream.PARENT, '')

    def test_catalog_generation_includes_metadata(self):
        """Test that generate_catalog includes parent-tap-stream-id in metadata for child streams."""
        # Test child stream includes parent-tap-stream-id
        campaign_opens_stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        catalog = campaign_opens_stream.generate_catalog()
        
        self.assertEqual(len(catalog), 1)
        catalog_entry = catalog[0]
        
        # Check metadata includes parent-tap-stream-id
        metadata_map = {item['breadcrumb']: item['metadata'] for item in catalog_entry['metadata']}
        self.assertIn('parent-tap-stream-id', metadata_map[tuple()])
        self.assertEqual(metadata_map[tuple()]['parent-tap-stream-id'], 'campaigns')

    def test_catalog_generation_excludes_parent_for_base_streams(self):
        """Test that generate_catalog does not include parent-tap-stream-id for base streams."""
        # Test base stream does not include parent-tap-stream-id
        campaigns_stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        catalog = campaigns_stream.generate_catalog()
        
        self.assertEqual(len(catalog), 1)
        catalog_entry = catalog[0]
        
        # Check metadata does not include parent-tap-stream-id
        metadata_map = {item['breadcrumb']: item['metadata'] for item in catalog_entry['metadata']}
        self.assertNotIn('parent-tap-stream-id', metadata_map[tuple()])

    def test_catalog_generation_key_properties_in_metadata(self):
        """Test that generate_catalog includes key properties with automatic inclusion."""
        campaign_opens_stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        catalog = campaign_opens_stream.generate_catalog()
        
        catalog_entry = catalog[0]
        metadata_map = {item['breadcrumb']: item['metadata'] for item in catalog_entry['metadata']}
        
        # Check that key properties have automatic inclusion
        for key_prop in campaign_opens_stream.KEY_PROPERTIES:
            breadcrumb = ('properties', key_prop)
            self.assertIn(breadcrumb, metadata_map)
            self.assertEqual(metadata_map[breadcrumb]['inclusion'], 'automatic')

    def test_catalog_generation_non_key_properties_available(self):
        """Test that generate_catalog marks non-key properties as available."""
        # Mock a schema with additional properties beyond key properties
        campaigns_stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        
        # Mock the schema to include additional properties
        original_get_schema = campaigns_stream.get_schema
        def mock_get_schema():
            schema = original_get_schema()
            # Add a non-key property to test
            if 'properties' not in schema:
                schema['properties'] = {}
            schema['properties']['Name'] = {'type': 'string'}
            schema['properties']['Subject'] = {'type': 'string'}
            return schema
        
        campaigns_stream.get_schema = mock_get_schema
        
        catalog = campaigns_stream.generate_catalog()
        catalog_entry = catalog[0]
        metadata_map = {item['breadcrumb']: item['metadata'] for item in catalog_entry['metadata']}
        
        # Check that non-key properties have available inclusion
        non_key_properties = ['Name', 'Subject']
        for prop in non_key_properties:
            breadcrumb = ('properties', prop)
            if breadcrumb in metadata_map:
                self.assertEqual(metadata_map[breadcrumb]['inclusion'], 'available')

    def test_requires_property_for_child_streams(self):
        """Test that child streams have correct REQUIRES property."""
        # Campaign child streams should require 'campaigns'
        campaign_opens_stream = CampaignOpensStream(self.config, self.state, self.catalog, self.client)
        self.assertIn('campaigns', campaign_opens_stream.REQUIRES)
        
        campaign_summary_stream = CampaignSummaryStream(self.config, self.state, self.catalog, self.client)
        self.assertIn('campaigns', campaign_summary_stream.REQUIRES)

        # List child streams should require 'lists'
        list_details_stream = ListDetailsStream(self.config, self.state, self.catalog, self.client)
        self.assertIn('lists', list_details_stream.REQUIRES)
        
        list_active_subscribers_stream = ListActiveSubscribersStream(self.config, self.state, self.catalog, self.client)
        self.assertIn('lists', list_active_subscribers_stream.REQUIRES)

    def test_requires_property_for_base_streams(self):
        """Test that base streams have empty REQUIRES property."""
        campaigns_stream = CampaignsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(campaigns_stream.REQUIRES, [])
        
        lists_stream = ListsStream(self.config, self.state, self.catalog, self.client)
        self.assertEqual(lists_stream.REQUIRES, [])

    def test_all_child_streams_have_parent_attribute(self):
        """Test that all child streams (inheriting from ChildStream) have PARENT attribute."""
        for stream_class in AVAILABLE_STREAMS:
            stream = stream_class(self.config, self.state, self.catalog, self.client)
            
            # If it's a child stream, it should have a non-empty PARENT
            if issubclass(stream_class, ChildStream) and stream_class != ChildStream:
                with self.subTest(stream_class=stream_class.__name__):
                    self.assertIsNotNone(stream.PARENT)
                    self.assertNotEqual(stream.PARENT, '')
                    self.assertIn(stream.PARENT, ['campaigns', 'lists'])

    def test_catalog_structure_consistency(self):
        """Test that catalog generation produces consistent structure for all streams."""
        for stream_class in AVAILABLE_STREAMS:
            with self.subTest(stream_class=stream_class.__name__):
                stream = stream_class(self.config, self.state, self.catalog, self.client)
                catalog = stream.generate_catalog()
                
                # Should return exactly one catalog entry
                self.assertEqual(len(catalog), 1)
                catalog_entry = catalog[0]
                
                # Check required fields exist
                required_fields = ['tap_stream_id', 'stream', 'key_properties', 'schema', 'metadata']
                for field in required_fields:
                    self.assertIn(field, catalog_entry)
                
                # Check that tap_stream_id matches TABLE
                self.assertEqual(catalog_entry['tap_stream_id'], stream.TABLE)
                self.assertEqual(catalog_entry['stream'], stream.TABLE)
                
                # Check that key_properties matches KEY_PROPERTIES
                self.assertEqual(catalog_entry['key_properties'], stream.KEY_PROPERTIES)
                
                # Check metadata is a list
                self.assertIsInstance(catalog_entry['metadata'], list)


if __name__ == '__main__':
    unittest.main()