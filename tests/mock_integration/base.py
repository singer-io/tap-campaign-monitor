"""
Base test class for mock integration tests for tap-campaign-monitor.

These tests run the real tap code against mocked API responses -- no external
tap-tester dependency required.

**Architecture**
* ``MockDataGenerator`` (in mock_data_generator.py) -- generic, reusable
  across any Singer tap.  Reads JSON schema files and produces
  deterministic, type-conformant mock records.
* ``STREAM_CONFIG`` / ``STREAM_URL_MATCHERS`` -- tap-specific configuration
  that describes response formats and URL routing.
* ``CampaignMonitorMockBaseTest`` -- tap-specific test base that wires
  the generator to the tap's real sync logic.
"""
import copy
import os
import unittest
from unittest.mock import MagicMock

import pytz
from singer import metadata, Catalog
from singer.catalog import CatalogEntry
from singer.schema import Schema

import tap_campaign_monitor
from tap_campaign_monitor.streams import AVAILABLE_STREAMS
from .mock_data_generator import MockDataGenerator


# ------------------------------------------------------------------ #
#  Tap-specific stream configuration
# ------------------------------------------------------------------ #

# Response types returned by the Campaign Monitor API:
#   list       -- flat JSON array of records
#   single     -- single JSON object (one record)
#   paginated  -- {Results:[...], NumberOfPages:N, ...}

STREAM_CONFIG = {
    # Parent streams
    'campaigns': {
        'response_type': 'list',
        'injected_field': None,
        'record_count': 1,
    },
    'lists': {
        'response_type': 'list',
        'injected_field': None,
        'record_count': 1,
    },
    # Campaign child streams
    'campaign_summary': {
        'response_type': 'single',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    'campaign_email_client_usage': {
        'response_type': 'list',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    'campaign_bounces': {
        'response_type': 'paginated',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    'campaign_clicks': {
        'response_type': 'paginated',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    'campaign_opens': {
        'response_type': 'paginated',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    'campaign_recipients': {
        'response_type': 'paginated',
        'injected_field': 'CampaignID',
        'record_count': 1,
        'ordered_by': 'email',
    },
    'campaign_spam_complaints': {
        'response_type': 'paginated',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    'campaign_unsubscribes': {
        'response_type': 'paginated',
        'injected_field': 'CampaignID',
        'record_count': 1,
    },
    # List child streams
    'list_details': {
        'response_type': 'single',
        'injected_field': 'ListID',
        'record_count': 1,
    },
    'list_active_subscribers': {
        'response_type': 'paginated',
        'injected_field': 'ListID',
        'record_count': 1,
    },
    'list_bounced_subscribers': {
        'response_type': 'paginated',
        'injected_field': 'ListID',
        'record_count': 1,
    },
    'list_deleted_subscribers': {
        'response_type': 'paginated',
        'injected_field': 'ListID',
        'record_count': 1,
    },
    'list_unconfirmed_subscribers': {
        'response_type': 'paginated',
        'injected_field': 'ListID',
        'record_count': 1,
    },
    'list_unsubscribed_subscribers': {
        'response_type': 'paginated',
        'injected_field': 'ListID',
        'record_count': 1,
    },
}

# URL matchers -- ordered so more specific patterns come first.
# Each entry: (stream_name, match_function)
STREAM_URL_MATCHERS = [
    # Campaign children
    ('campaign_summary',
     lambda url: '/campaigns/' in url and '/summary.json' in url),
    ('campaign_bounces',
     lambda url: '/campaigns/' in url and '/bounces.json' in url),
    ('campaign_clicks',
     lambda url: '/campaigns/' in url and '/clicks.json' in url),
    ('campaign_opens',
     lambda url: '/campaigns/' in url and '/opens.json' in url),
    ('campaign_recipients',
     lambda url: '/campaigns/' in url and '/recipients.json' in url),
    ('campaign_spam_complaints',
     lambda url: '/campaigns/' in url and '/spam.json' in url),
    ('campaign_unsubscribes',
     lambda url: '/campaigns/' in url and '/unsubscribes.json' in url),
    ('campaign_email_client_usage',
     lambda url: '/campaigns/' in url and '/emailclientusage.json' in url),
    # List children
    ('list_active_subscribers',
     lambda url: '/lists/' in url and '/active.json' in url),
    ('list_bounced_subscribers',
     lambda url: '/lists/' in url and '/bounced.json' in url),
    ('list_deleted_subscribers',
     lambda url: '/lists/' in url and '/deleted.json' in url),
    ('list_unconfirmed_subscribers',
     lambda url: '/lists/' in url and '/unconfirmed.json' in url),
    ('list_unsubscribed_subscribers',
     lambda url: '/lists/' in url and '/unsubscribed.json' in url),
    ('list_details',
     lambda url: '/lists/' in url and url.endswith('.json')
     and '/active' not in url and '/bounced' not in url
     and '/deleted' not in url and '/unconfirmed' not in url
     and '/unsubscribed' not in url),
    # Parent streams (broadest patterns last)
    ('campaigns',
     lambda url: url.endswith('/campaigns.json')),
    ('lists',
     lambda url: url.endswith('/lists.json') and '/lists/' not in url),
]

# Parent-stream -> ID-field mapping
PARENT_ID_FIELDS = {
    'campaigns': 'CampaignID',
    'lists': 'ListID',
}

# Streams that get multi-page treatment in pagination tests
MULTI_PAGE_STREAMS = {
    'campaign_bounces', 'campaign_recipients', 'list_active_subscribers',
}

# Seed for pagination page 2 (page 1 uses base_seed=0)
PAGE2_SEED = 10

# Seed used for "recent" records in date-filter tests
RECENT_DATA_SEED = 100


# ------------------------------------------------------------------ #
#  Test base class
# ------------------------------------------------------------------ #

class CampaignMonitorMockBaseTest:
    """Shared helpers and dynamically-generated mock data for
    campaign-monitor mock integration tests."""

    PRIMARY_KEYS = "primary_keys"
    REPLICATION_METHOD = "replication_method"

    STREAM_CONFIG = STREAM_CONFIG

    default_config = {
        "client_id": "mock-client-id-12345",
        "refresh_token": "mock-refresh-token-67890",
    }

    # Lazily initialised MockDataGenerator
    _generator = None

    ALL_STREAM_IDS = set(STREAM_CONFIG.keys())

    # ------------------------------------------------------------------ #
    #  Generator access
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_generator(cls):
        """Return (or create) the shared MockDataGenerator."""
        if cls._generator is None:
            schemas_dir = os.path.join(
                os.path.dirname(__file__), '..', '..',
                'tap_campaign_monitor', 'schemas')
            cls._generator = MockDataGenerator(
                os.path.normpath(schemas_dir))
        return cls._generator

    # ------------------------------------------------------------------ #
    #  Convenience helpers for tests
    # ------------------------------------------------------------------ #

    @classmethod
    def get_mock_parent_id(cls, parent_stream):
        """Return the deterministic mock ID for a parent stream (seed=0)."""
        gen = cls._get_generator()
        field = PARENT_ID_FIELDS[parent_stream]
        record = gen.generate_record(parent_stream, seed=0)
        return record[field]

    @classmethod
    def get_bookmark_key(cls, parent_stream, child_stream):
        """Return the expected bookmark key: ``<parent_id>.<child_table>``."""
        return "{}.{}".format(
            cls.get_mock_parent_id(parent_stream), child_stream)

    @classmethod
    def get_expected_record_count(cls, stream_name):
        """Number of records the default mock client returns for a stream."""
        return STREAM_CONFIG[stream_name]['record_count']

    @classmethod
    def get_mock_records(cls, stream_name, count=None, base_seed=0):
        """Return the mock records that the API would return for a stream."""
        gen = cls._get_generator()
        config = STREAM_CONFIG[stream_name]
        exclude = ({config['injected_field']}
                   if config['injected_field'] else set())
        n = count if count is not None else config['record_count']
        return gen.generate_records(
            stream_name, n, base_seed=base_seed,
            exclude_fields=exclude)

    @classmethod
    def get_initial_bookmark_date(cls):
        """A date guaranteed to be *before* any generated mock date."""
        from datetime import timedelta
        dt = MockDataGenerator.BASE_DATE - timedelta(days=1)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def get_recent_record(cls, stream_name):
        """Return the 'recent' mock record used in date-filter tests."""
        return cls.get_mock_records(
            stream_name, count=1, base_seed=RECENT_DATA_SEED)[0]

    @classmethod
    def get_recent_date(cls, stream_name):
        """Return the Date value from the 'recent' mock record."""
        return cls.get_recent_record(stream_name).get('Date', '')

    # ------------------------------------------------------------------ #
    #  Expected metadata
    # ------------------------------------------------------------------ #

    @classmethod
    def expected_metadata(cls):
        return {
            "campaigns": {
                cls.PRIMARY_KEYS: {"CampaignID"},
            },
            "campaign_bounces": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
            },
            "campaign_clicks": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
            },
            "campaign_email_client_usage": {
                cls.PRIMARY_KEYS: {"CampaignID", "Client", "Version"},
            },
            "campaign_opens": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
            },
            "campaign_recipients": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress"},
            },
            "campaign_spam_complaints": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
            },
            "campaign_summary": {
                cls.PRIMARY_KEYS: {"CampaignID"},
            },
            "campaign_unsubscribes": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
            },
            "lists": {
                cls.PRIMARY_KEYS: {"ListID"},
            },
            "list_active_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
            },
            "list_bounced_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
            },
            "list_deleted_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
            },
            "list_details": {
                cls.PRIMARY_KEYS: {"ListID"},
            },
            "list_unconfirmed_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
            },
            "list_unsubscribed_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
            },
        }

    # ------------------------------------------------------------------ #
    #  Mock client factories
    # ------------------------------------------------------------------ #

    @classmethod
    def _build_response(cls, stream_name, records):
        """Wrap *records* according to the stream's response_type."""
        config = STREAM_CONFIG[stream_name]
        rtype = config['response_type']
        if rtype == 'list':
            return copy.deepcopy(records)
        if rtype == 'single':
            return copy.deepcopy(records[0])
        if rtype == 'paginated':
            ordered_by = config.get('ordered_by', 'date')
            return copy.deepcopy(
                MockDataGenerator.wrap_paginated(
                    records, ordered_by=ordered_by))
        return copy.deepcopy(records)

    @classmethod
    def _match_stream(cls, url):
        """Return the stream name matching *url*, or None."""
        for stream_name, matcher in STREAM_URL_MATCHERS:
            if matcher(url):
                return stream_name
        return None

    @classmethod
    def _create_mock_client(cls):
        """Create a mock CampaignMonitorClient with dynamically
        generated responses (single-page)."""
        client = MagicMock()
        client.timezone = pytz.UTC
        client.config = dict(cls.default_config)
        client.make_request = MagicMock(
            side_effect=cls._mock_make_request())
        return client

    @classmethod
    def _mock_make_request(cls):
        """Side-effect: dispatches by URL, generates data from schemas."""
        gen = cls._get_generator()

        def mock_fn(url, method, params=None, body=None):
            stream_name = cls._match_stream(url)
            if stream_name:
                config = STREAM_CONFIG[stream_name]
                exclude = ({config['injected_field']}
                           if config['injected_field'] else set())
                records = gen.generate_records(
                    stream_name, config['record_count'],
                    exclude_fields=exclude)
                return cls._build_response(stream_name, records)

            # Client timezone endpoint
            if '/clients/' in url and url.endswith('.json'):
                return {
                    "BasicDetails": {
                        "TimeZone": "(GMT) Coordinated Universal Time"
                    }
                }
            return []

        return mock_fn

    # ---- Paginated mock client ---- #

    @classmethod
    def _create_paginated_mock_client(cls):
        """Mock client that returns 2-page results for streams in
        ``MULTI_PAGE_STREAMS``."""
        client = MagicMock()
        client.timezone = pytz.UTC
        client.config = dict(cls.default_config)
        client.make_request = MagicMock(
            side_effect=cls._mock_make_request_paginated())
        return client

    @classmethod
    def _mock_make_request_paginated(cls):
        gen = cls._get_generator()

        def mock_fn(url, method, params=None, body=None):
            page = (params or {}).get('page', 1)
            stream_name = cls._match_stream(url)

            if stream_name:
                config = STREAM_CONFIG[stream_name]
                exclude = ({config['injected_field']}
                           if config['injected_field'] else set())
                ordered_by = config.get('ordered_by', 'date')

                # Multi-page for selected streams
                if (config['response_type'] == 'paginated'
                        and stream_name in MULTI_PAGE_STREAMS):
                    seed = 0 if page == 1 else PAGE2_SEED
                    records = gen.generate_records(
                        stream_name, 1, base_seed=seed,
                        exclude_fields=exclude)
                    return copy.deepcopy(
                        MockDataGenerator.wrap_paginated(
                            records, page=page, total_pages=2,
                            ordered_by=ordered_by))

                # Single-page (default)
                records = gen.generate_records(
                    stream_name, config['record_count'],
                    exclude_fields=exclude)
                return cls._build_response(stream_name, records)

            if '/clients/' in url and url.endswith('.json'):
                return {
                    "BasicDetails": {
                        "TimeZone": "(GMT) Coordinated Universal Time"
                    }
                }
            return []

        return mock_fn

    # ---- Date-filtering mock client ---- #

    @classmethod
    def _create_date_filtering_mock_client(cls):
        """Mock client that returns different results when a ``date``
        param is present (simulating bookmark-based filtering)."""
        client = MagicMock()
        client.timezone = pytz.UTC
        client.config = dict(cls.default_config)
        client.make_request = MagicMock(
            side_effect=cls._mock_make_request_date_filter())
        return client

    @classmethod
    def _mock_make_request_date_filter(cls):
        gen = cls._get_generator()

        def mock_fn(url, method, params=None, body=None):
            date_param = (params or {}).get('date')
            stream_name = cls._match_stream(url)

            if stream_name:
                config = STREAM_CONFIG[stream_name]
                exclude = ({config['injected_field']}
                           if config['injected_field'] else set())
                ordered_by = config.get('ordered_by', 'date')

                # Date-filtered: return "recent" data with higher seed
                if config['response_type'] == 'paginated' and date_param:
                    records = gen.generate_records(
                        stream_name, 1, base_seed=RECENT_DATA_SEED,
                        exclude_fields=exclude)
                    return copy.deepcopy(
                        MockDataGenerator.wrap_paginated(
                            records, ordered_by=ordered_by))

                # Normal response
                records = gen.generate_records(
                    stream_name, config['record_count'],
                    exclude_fields=exclude)
                return cls._build_response(stream_name, records)

            if '/clients/' in url and url.endswith('.json'):
                return {
                    "BasicDetails": {
                        "TimeZone": "(GMT) Coordinated Universal Time"
                    }
                }
            return []

        return mock_fn

    # ------------------------------------------------------------------ #
    #  Discover / catalog helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def _build_standard_metadata(cls, schema, key_properties,
                                 valid_replication_keys,
                                 replication_method):
        """Replacement for ``singer.metadata.get_standard_metadata``
        which may not exist in the installed singer-python version."""
        from singer import metadata as meta
        mdata = meta.new()
        mdata = meta.write(mdata, (), 'table-key-properties', key_properties)
        mdata = meta.write(mdata, (), 'forced-replication-method',
                           replication_method)
        if valid_replication_keys:
            mdata = meta.write(mdata, (), 'valid-replication-keys',
                               valid_replication_keys)
        for field_name in schema.get('properties', {}):
            if field_name in (key_properties or []):
                mdata = meta.write(mdata, ('properties', field_name),
                                   'inclusion', 'automatic')
            else:
                mdata = meta.write(mdata, ('properties', field_name),
                                   'inclusion', 'available')
        return meta.to_list(mdata)

    @classmethod
    def _run_discover(cls):
        """Run discovery using real stream classes and return catalog
        entry dicts."""
        from singer import metadata as meta

        config = dict(cls.default_config)
        state = {}

        needs_patch = not hasattr(meta, 'get_standard_metadata')
        if needs_patch:
            def _gsm(schema=None, key_properties=None,
                     valid_replication_keys=None,
                     replication_method=None):
                return cls._build_standard_metadata(
                    schema, key_properties,
                    valid_replication_keys, replication_method)
            meta.get_standard_metadata = _gsm

        try:
            catalog_entries = []
            for available_stream in AVAILABLE_STREAMS:
                stream = available_stream(config, state, None, None)
                catalog_entries += stream.generate_catalog()
        finally:
            if needs_patch:
                del meta.get_standard_metadata

        return catalog_entries

    @classmethod
    def _make_selected_catalog(cls, stream_names=None):
        """Build a Catalog with ``selected=True`` for *stream_names*
        (default: all)."""
        raw_entries = cls._run_discover()
        catalog_entries = []

        for entry_dict in raw_entries:
            is_selected = (stream_names is None
                           or entry_dict['tap_stream_id'] in stream_names)

            mdata = metadata.to_map(entry_dict['metadata'])
            mdata = metadata.write(mdata, (), 'selected', is_selected)

            for field_name in entry_dict['schema'].get('properties', {}):
                mdata = metadata.write(
                    mdata, ('properties', field_name),
                    'selected', is_selected)

            catalog_entries.append(CatalogEntry(
                tap_stream_id=entry_dict['tap_stream_id'],
                stream=entry_dict['stream'],
                key_properties=entry_dict['key_properties'],
                schema=Schema.from_dict(entry_dict['schema']),
                metadata=metadata.to_list(mdata),
            ))

        return Catalog(catalog_entries)

    @classmethod
    def _make_automatic_fields_catalog(cls, stream_names=None):
        """Build a Catalog with only automatic (PK) fields selected."""
        raw_entries = cls._run_discover()
        expected = cls.expected_metadata()
        catalog_entries = []

        for entry_dict in raw_entries:
            is_selected = (stream_names is None
                           or entry_dict['tap_stream_id'] in stream_names)

            pk_fields = expected.get(
                entry_dict['tap_stream_id'], {}).get(
                    cls.PRIMARY_KEYS, set())

            mdata = metadata.to_map(entry_dict['metadata'])
            mdata = metadata.write(mdata, (), 'selected', is_selected)

            for field_name in entry_dict['schema'].get('properties', {}):
                mdata = metadata.write(
                    mdata, ('properties', field_name),
                    'selected', field_name in pk_fields)

            catalog_entries.append(CatalogEntry(
                tap_stream_id=entry_dict['tap_stream_id'],
                stream=entry_dict['stream'],
                key_properties=entry_dict['key_properties'],
                schema=Schema.from_dict(entry_dict['schema']),
                metadata=metadata.to_list(mdata),
            ))

        return Catalog(catalog_entries)

    # ------------------------------------------------------------------ #
    #  Sync runner
    # ------------------------------------------------------------------ #

    @classmethod
    def _run_sync(cls, catalog, state=None, client=None):
        """Run sync using real tap code with the given (mock) client."""
        config = dict(cls.default_config)
        if state is None:
            state = {}
        if client is None:
            client = cls._create_mock_client()

        streams, campaign_substreams, list_substreams = \
            tap_campaign_monitor.get_streams_to_replicate(
                config, state, catalog, client)

        for stream in streams:
            substreams = []
            if stream.TABLE == 'campaigns':
                substreams = campaign_substreams
            elif stream.TABLE == 'lists':
                substreams = list_substreams

            stream.state = state
            stream.sync(substreams=substreams)
            state = stream.state

            # Substreams update their own self.state via incorporate();
            # merge those changes back so the returned state is complete.
            for sub in substreams:
                for key, val in sub.state.get('bookmarks', {}).items():
                    state.setdefault('bookmarks', {})[key] = val

        return state
