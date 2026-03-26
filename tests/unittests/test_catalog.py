import json
import os
import unittest


SCHEMA_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'tap_campaign_monitor', 'schemas')

EXPECTED_STREAMS = {
    'campaigns', 'campaign_bounces', 'campaign_clicks',
    'campaign_email_client_usage', 'campaign_opens',
    'campaign_recipients', 'campaign_spam_complaints',
    'campaign_summary', 'campaign_unsubscribes',
    'lists', 'list_active_subscribers', 'list_bounced_subscribers',
    'list_deleted_subscribers', 'list_details',
    'list_unconfirmed_subscribers', 'list_unsubscribed_subscribers',
}


class TestCatalogGeneration(unittest.TestCase):
    """Test that catalog / discover output is valid."""

    def test_all_streams_have_schema_files(self):
        """Each stream in AVAILABLE_STREAMS should have a matching schema JSON."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            schema_file = os.path.join(SCHEMA_DIR, f'{stream_cls.TABLE}.json')
            self.assertTrue(
                os.path.exists(schema_file),
                f'Missing schema file for {stream_cls.TABLE}')

    def test_schema_files_are_valid_json(self):
        """Every .json file in schemas/ should parse as valid JSON."""
        for filename in os.listdir(SCHEMA_DIR):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(SCHEMA_DIR, filename)
            with open(filepath) as f:
                try:
                    schema = json.load(f)
                except json.JSONDecodeError:
                    self.fail(f'{filename} is not valid JSON')
            self.assertIn('type', schema,
                          f'{filename} missing top-level "type"')
            self.assertIn('properties', schema,
                          f'{filename} missing "properties"')

    def test_generate_catalog_returns_correct_structure(self):
        """generate_catalog should return list of dicts with required keys."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            inst = stream_cls({}, {}, None, None)
            catalog = inst.generate_catalog()
            self.assertIsInstance(catalog, list)
            for entry in catalog:
                self.assertIn('tap_stream_id', entry)
                self.assertIn('stream', entry)
                self.assertIn('key_properties', entry)
                self.assertIn('schema', entry)
                self.assertIn('metadata', entry)
                self.assertEqual(entry['tap_stream_id'], stream_cls.TABLE)
                self.assertEqual(entry['key_properties'], stream_cls.KEY_PROPERTIES)

    def test_expected_streams_match_available_streams(self):
        """AVAILABLE_STREAMS should contain exactly the expected streams."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        actual = {s.TABLE for s in AVAILABLE_STREAMS}
        self.assertEqual(actual, EXPECTED_STREAMS)

    def test_key_properties_in_schema(self):
        """All KEY_PROPERTIES should exist in the stream's schema."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            schema_file = os.path.join(SCHEMA_DIR, f'{stream_cls.TABLE}.json')
            with open(schema_file) as f:
                schema = json.load(f)
            schema_fields = set(schema.get('properties', {}).keys())
            for key in stream_cls.KEY_PROPERTIES:
                self.assertIn(
                    key, schema_fields,
                    f'{stream_cls.TABLE}: KEY_PROPERTY "{key}" not in schema')

    def test_metadata_has_automatic_for_key_properties(self):
        """Key properties should have inclusion=automatic in metadata."""
        from tap_campaign_monitor.streams import AVAILABLE_STREAMS
        for stream_cls in AVAILABLE_STREAMS:
            inst = stream_cls({}, {}, None, None)
            catalog = inst.generate_catalog()
            for entry in catalog:
                metadata_map = {
                    tuple(m['breadcrumb']): m['metadata']
                    for m in entry['metadata']
                }
                for key_prop in stream_cls.KEY_PROPERTIES:
                    breadcrumb = ('properties', key_prop)
                    self.assertIn(breadcrumb, metadata_map,
                                  f'{stream_cls.TABLE}: missing metadata for {key_prop}')
                    self.assertEqual(
                        metadata_map[breadcrumb].get('inclusion'), 'automatic',
                        f'{stream_cls.TABLE}: {key_prop} should be automatic')

    def test_datetime_fields_have_format(self):
        """Fields ending in _time, _date, Date, or Time should have date-time format."""
        datetime_field_suffixes = ('_time', '_date', 'Date', 'Time')
        exact_datetime_fields = ('Date', 'SentDate', 'created_time', 'modified_time')

        for filename in os.listdir(SCHEMA_DIR):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(SCHEMA_DIR, filename)
            with open(filepath) as f:
                schema = json.load(f)
            for field_name, field_schema in schema.get('properties', {}).items():
                is_datetime = (
                    field_name in exact_datetime_fields or
                    any(field_name.endswith(s) for s in datetime_field_suffixes)
                )
                if is_datetime and 'string' in (field_schema.get('type', []) if isinstance(field_schema.get('type'), list) else [field_schema.get('type', '')]):
                    self.assertEqual(
                        field_schema.get('format'), 'date-time',
                        f'{filename}: {field_name} should have format=date-time')


if __name__ == '__main__':
    unittest.main()
