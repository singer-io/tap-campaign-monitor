"""
Base test class for mock integration tests for tap-campaign-monitor.

These tests run the real tap code against mocked API responses — no external
tap-tester dependency required.
"""
import copy
import json
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

import pytz
from singer import metadata, Catalog
from singer.catalog import CatalogEntry
from singer.schema import Schema

import tap_campaign_monitor
from tap_campaign_monitor.streams import AVAILABLE_STREAMS


class CampaignMonitorMockBaseTest:
    """Shared helpers and mock data for campaign-monitor mock integration tests."""

    PRIMARY_KEYS = "primary_keys"
    REPLICATION_METHOD = "replication_method"

    default_config = {
        "client_id": "mock-client-id-12345",
        "refresh_token": "mock-refresh-token-67890",
    }

    # ------------------------------------------------------------------ #
    #  Mock API data
    # ------------------------------------------------------------------ #

    MOCK_CAMPAIGNS = [
        {
            "CampaignID": "camp-001",
            "FromName": "Test Sender",
            "FromEmail": "sender@example.com",
            "ReplyTo": "reply@example.com",
            "WebVersionURL": "https://example.com/web/camp1",
            "WebVersionTextURL": "https://example.com/web/camp1/text",
            "Subject": "Test Campaign One",
            "Name": "Campaign Alpha",
            "SentDate": "2024-06-15 10:00:00",
            "TotalRecipients": 150,
        },
    ]

    MOCK_LISTS = [
        {
            "ListID": "list-001",
            "Name": "Newsletter Subscribers",
        },
    ]

    MOCK_CAMPAIGN_SUMMARY = {
        "Recipients": 150,
        "TotalOpened": 80,
        "Clicks": 25,
        "Unsubscribed": 3,
        "Bounced": 2,
        "UniqueOpened": 60,
        "SpamComplaints": 0,
        "WebVersionURL": "https://example.com/web/camp1",
        "WebVersionTextURL": "https://example.com/web/camp1/text",
        "WorldviewURL": "https://example.com/worldview/camp1",
        "Forwards": 5,
        "Likes": 10,
        "Mentions": 2,
    }

    MOCK_CAMPAIGN_BOUNCES = {
        "Results": [
            {
                "EmailAddress": "bounce@example.com",
                "ListID": "list-001",
                "Date": "2024-06-16 08:00:00",
                "BounceType": "Hard",
                "Reason": "Mailbox not found",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_CAMPAIGN_CLICKS = {
        "Results": [
            {
                "EmailAddress": "click@example.com",
                "ListID": "list-001",
                "Date": "2024-06-16 09:30:00",
                "URL": "https://example.com/link1",
                "IPAddress": "192.168.1.1",
                "Latitude": 40.7128,
                "Longitude": -74.006,
                "City": "New York",
                "Region": "NY",
                "CountryCode": "US",
                "CountryName": "United States",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_CAMPAIGN_OPENS = {
        "Results": [
            {
                "EmailAddress": "opener@example.com",
                "ListID": "list-001",
                "Date": "2024-06-16 07:00:00",
                "IPAddress": "10.0.0.1",
                "Latitude": 51.5074,
                "Longitude": -0.1278,
                "City": "London",
                "Region": "England",
                "CountryCode": "GB",
                "CountryName": "United Kingdom",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_CAMPAIGN_RECIPIENTS = {
        "Results": [
            {
                "EmailAddress": "recipient@example.com",
                "ListID": "list-001",
            },
        ],
        "ResultsOrderedBy": "email",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_CAMPAIGN_SPAM_COMPLAINTS = {
        "Results": [
            {
                "EmailAddress": "spam@example.com",
                "ListID": "list-001",
                "Date": "2024-06-17 12:00:00",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_CAMPAIGN_UNSUBSCRIBES = {
        "Results": [
            {
                "EmailAddress": "unsub@example.com",
                "ListID": "list-001",
                "Date": "2024-06-18 14:00:00",
                "IPAddress": "172.16.0.1",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_CAMPAIGN_EMAIL_CLIENT_USAGE = [
        {
            "Client": "Gmail",
            "Version": "—",
            "Percentage": 45.5,
            "Subscribers": 68,
        },
    ]

    MOCK_LIST_DETAILS = {
        "ConfirmedOptIn": False,
        "Title": "Newsletter Subscribers",
        "UnsubscribePage": "",
        "UnsubscribeSetting": "AllClientLists",
        "ConfirmationSuccessPage": "",
    }

    MOCK_LIST_ACTIVE_SUBSCRIBERS = {
        "Results": [
            {
                "EmailAddress": "active@example.com",
                "Date": "2024-01-15 10:00:00",
                "Name": "Active User",
                "State": "Active",
                "CustomFields": [],
                "ReadsEmailWith": "Gmail",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_LIST_BOUNCED_SUBSCRIBERS = {
        "Results": [
            {
                "EmailAddress": "bounced@example.com",
                "Date": "2024-02-10 11:00:00",
                "Name": "Bounced User",
                "State": "Bounced",
                "CustomFields": [],
                "ReadsEmailWith": "",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_LIST_DELETED_SUBSCRIBERS = {
        "Results": [
            {
                "EmailAddress": "deleted@example.com",
                "Date": "2024-03-05 09:00:00",
                "Name": "Deleted User",
                "State": "Deleted",
                "CustomFields": [],
                "ReadsEmailWith": "",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_LIST_UNCONFIRMED_SUBSCRIBERS = {
        "Results": [
            {
                "EmailAddress": "unconfirmed@example.com",
                "Date": "2024-04-20 15:00:00",
                "Name": "Unconfirmed User",
                "State": "Unconfirmed",
                "CustomFields": [],
                "ReadsEmailWith": "",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    MOCK_LIST_UNSUBSCRIBED_SUBSCRIBERS = {
        "Results": [
            {
                "EmailAddress": "listunsub@example.com",
                "Date": "2024-05-10 16:00:00",
                "Name": "Unsubscribed User",
                "State": "Unsubscribed",
                "CustomFields": [],
                "ReadsEmailWith": "Outlook",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    ALL_STREAM_IDS = {
        "campaigns", "campaign_bounces", "campaign_clicks",
        "campaign_email_client_usage", "campaign_opens",
        "campaign_recipients", "campaign_spam_complaints",
        "campaign_summary", "campaign_unsubscribes",
        "lists", "list_active_subscribers", "list_bounced_subscribers",
        "list_deleted_subscribers", "list_details",
        "list_unconfirmed_subscribers", "list_unsubscribed_subscribers",
    }

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
    # Mock client factory
    # ------------------------------------------------------------------ #

    @classmethod
    def _create_mock_client(cls):
        """Create a mock CampaignMonitorClient with mocked make_request."""
        client = MagicMock()
        client.timezone = pytz.UTC
        client.config = dict(cls.default_config)
        client.make_request = MagicMock(side_effect=cls._mock_make_request())
        return client

    @classmethod
    def _mock_make_request(cls):
        """Return a side_effect function that dispatches by URL."""

        def mock_fn(url, method, params=None, body=None):
            # campaigns parent
            if url.endswith("/campaigns.json"):
                return copy.deepcopy(cls.MOCK_CAMPAIGNS)

            # lists parent
            if url.endswith("/lists.json") and "/lists/" not in url:
                return copy.deepcopy(cls.MOCK_LISTS)

            # campaign child endpoints
            if "/campaigns/" in url:
                if "/summary.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_SUMMARY)
                if "/bounces.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_BOUNCES)
                if "/clicks.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_CLICKS)
                if "/opens.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_OPENS)
                if "/recipients.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_RECIPIENTS)
                if "/spam.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_SPAM_COMPLAINTS)
                if "/unsubscribes.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_UNSUBSCRIBES)
                if "/emailclientusage.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_EMAIL_CLIENT_USAGE)

            # list child endpoints
            if "/lists/" in url:
                if url.endswith(".json") and "/active" not in url and "/bounced" not in url \
                        and "/deleted" not in url and "/unconfirmed" not in url \
                        and "/unsubscribed" not in url:
                    return copy.deepcopy(cls.MOCK_LIST_DETAILS)
                if "/active.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_ACTIVE_SUBSCRIBERS)
                if "/bounced.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_BOUNCED_SUBSCRIBERS)
                if "/deleted.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_DELETED_SUBSCRIBERS)
                if "/unconfirmed.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_UNCONFIRMED_SUBSCRIBERS)
                if "/unsubscribed.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_UNSUBSCRIBED_SUBSCRIBERS)

            # client timezone endpoint
            if "/clients/" in url and url.endswith(".json"):
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
    def _build_standard_metadata(cls, schema, key_properties, valid_replication_keys, replication_method):
        """Replacement for singer.metadata.get_standard_metadata which may
        not exist in the installed singer-python version.
        Returns metadata in list format (as get_standard_metadata would)."""
        from singer import metadata as meta
        mdata = meta.new()

        mdata = meta.write(mdata, (), 'table-key-properties', key_properties)
        mdata = meta.write(mdata, (), 'forced-replication-method', replication_method)
        if valid_replication_keys:
            mdata = meta.write(mdata, (), 'valid-replication-keys', valid_replication_keys)

        for field_name in schema.get('properties', {}):
            if field_name in (key_properties or []):
                mdata = meta.write(mdata, ('properties', field_name), 'inclusion', 'automatic')
            else:
                mdata = meta.write(mdata, ('properties', field_name), 'inclusion', 'available')

        return meta.to_list(mdata)

    @classmethod
    def _run_discover(cls):
        """Run discovery using real stream classes and return catalog entries.
        
        Patches singer.metadata.get_standard_metadata if it doesn't exist
        so that generate_catalog() works.
        """
        from singer import metadata as meta

        config = dict(cls.default_config)
        state = {}

        # Provide get_standard_metadata if missing
        needs_patch = not hasattr(meta, 'get_standard_metadata')
        if needs_patch:
            def _get_standard_metadata(schema=None, key_properties=None,
                                       valid_replication_keys=None,
                                       replication_method=None):
                return cls._build_standard_metadata(
                    schema, key_properties,
                    valid_replication_keys, replication_method)
            meta.get_standard_metadata = _get_standard_metadata

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
        """Build a Catalog with selected=True for the given streams.
        If stream_names is None, select all streams.
        """
        raw_entries = cls._run_discover()
        catalog_entries = []

        for entry_dict in raw_entries:
            is_selected = (stream_names is None
                           or entry_dict['tap_stream_id'] in stream_names)

            mdata = metadata.to_map(entry_dict['metadata'])
            mdata = metadata.write(mdata, (), 'selected', is_selected)

            # Also select all fields
            for field_name in entry_dict['schema'].get('properties', {}):
                mdata = metadata.write(
                    mdata, ('properties', field_name), 'selected', is_selected)

            catalog_entry = CatalogEntry(
                tap_stream_id=entry_dict['tap_stream_id'],
                stream=entry_dict['stream'],
                key_properties=entry_dict['key_properties'],
                schema=Schema.from_dict(entry_dict['schema']),
                metadata=metadata.to_list(mdata),
            )
            catalog_entries.append(catalog_entry)

        return Catalog(catalog_entries)

    @classmethod
    def _make_automatic_fields_catalog(cls, stream_names=None):
        """Build a Catalog with selected=True but only automatic (PK) fields selected.
        Non-PK fields are deselected so only automatic fields are replicated.
        """
        raw_entries = cls._run_discover()
        expected = cls.expected_metadata()
        catalog_entries = []

        for entry_dict in raw_entries:
            is_selected = (stream_names is None
                           or entry_dict['tap_stream_id'] in stream_names)

            pk_fields = expected.get(
                entry_dict['tap_stream_id'], {}).get(cls.PRIMARY_KEYS, set())

            mdata = metadata.to_map(entry_dict['metadata'])
            mdata = metadata.write(mdata, (), 'selected', is_selected)

            for field_name in entry_dict['schema'].get('properties', {}):
                if field_name in pk_fields:
                    mdata = metadata.write(
                        mdata, ('properties', field_name), 'selected', True)
                else:
                    mdata = metadata.write(
                        mdata, ('properties', field_name), 'selected', False)

            catalog_entry = CatalogEntry(
                tap_stream_id=entry_dict['tap_stream_id'],
                stream=entry_dict['stream'],
                key_properties=entry_dict['key_properties'],
                schema=Schema.from_dict(entry_dict['schema']),
                metadata=metadata.to_list(mdata),
            )
            catalog_entries.append(catalog_entry)

        return Catalog(catalog_entries)

    # ------------------------------------------------------------------ #
    #  Paginated mock client
    # ------------------------------------------------------------------ #

    MOCK_CAMPAIGN_BOUNCES_PAGE1 = {
        "Results": [
            {
                "EmailAddress": "bounce1@example.com",
                "ListID": "list-001",
                "Date": "2024-06-16 08:00:00",
                "BounceType": "Hard",
                "Reason": "Mailbox not found",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 2,
        "NumberOfPages": 2,
    }

    MOCK_CAMPAIGN_BOUNCES_PAGE2 = {
        "Results": [
            {
                "EmailAddress": "bounce2@example.com",
                "ListID": "list-001",
                "Date": "2024-06-17 09:00:00",
                "BounceType": "Soft",
                "Reason": "Mailbox full",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 2,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 2,
        "NumberOfPages": 2,
    }

    MOCK_CAMPAIGN_RECIPIENTS_PAGE1 = {
        "Results": [
            {
                "EmailAddress": "recipient1@example.com",
                "ListID": "list-001",
            },
        ],
        "ResultsOrderedBy": "email",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 2,
        "NumberOfPages": 2,
    }

    MOCK_CAMPAIGN_RECIPIENTS_PAGE2 = {
        "Results": [
            {
                "EmailAddress": "recipient2@example.com",
                "ListID": "list-001",
            },
        ],
        "ResultsOrderedBy": "email",
        "OrderDirection": "asc",
        "PageNumber": 2,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 2,
        "NumberOfPages": 2,
    }

    MOCK_LIST_ACTIVE_SUBSCRIBERS_PAGE1 = {
        "Results": [
            {
                "EmailAddress": "active1@example.com",
                "Date": "2024-01-15 10:00:00",
                "Name": "Active User 1",
                "State": "Active",
                "CustomFields": [],
                "ReadsEmailWith": "Gmail",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 2,
        "NumberOfPages": 2,
    }

    MOCK_LIST_ACTIVE_SUBSCRIBERS_PAGE2 = {
        "Results": [
            {
                "EmailAddress": "active2@example.com",
                "Date": "2024-02-20 11:00:00",
                "Name": "Active User 2",
                "State": "Active",
                "CustomFields": [],
                "ReadsEmailWith": "Outlook",
                "ConsentToTrack": "Yes",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 2,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 2,
        "NumberOfPages": 2,
    }

    @classmethod
    def _create_paginated_mock_client(cls):
        """Create a mock client that returns multi-page results for
        paginated streams while keeping single-page results for others."""
        client = MagicMock()
        client.timezone = pytz.UTC
        client.config = dict(cls.default_config)
        client.make_request = MagicMock(
            side_effect=cls._mock_make_request_paginated())
        return client

    @classmethod
    def _mock_make_request_paginated(cls):
        """Side-effect function that returns multi-page data for
        paginated endpoints (bounces, recipients, active subscribers)."""

        def mock_fn(url, method, params=None, body=None):
            page = (params or {}).get('page', 1)

            # campaigns parent
            if url.endswith("/campaigns.json"):
                return copy.deepcopy(cls.MOCK_CAMPAIGNS)

            # lists parent
            if url.endswith("/lists.json") and "/lists/" not in url:
                return copy.deepcopy(cls.MOCK_LISTS)

            # campaign child endpoints with pagination
            if "/campaigns/" in url:
                if "/bounces.json" in url:
                    if page == 1:
                        return copy.deepcopy(cls.MOCK_CAMPAIGN_BOUNCES_PAGE1)
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_BOUNCES_PAGE2)
                if "/recipients.json" in url:
                    if page == 1:
                        return copy.deepcopy(cls.MOCK_CAMPAIGN_RECIPIENTS_PAGE1)
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_RECIPIENTS_PAGE2)
                if "/summary.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_SUMMARY)
                if "/clicks.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_CLICKS)
                if "/opens.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_OPENS)
                if "/spam.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_SPAM_COMPLAINTS)
                if "/unsubscribes.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_UNSUBSCRIBES)
                if "/emailclientusage.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_EMAIL_CLIENT_USAGE)

            # list child endpoints with pagination
            if "/lists/" in url:
                if "/active.json" in url:
                    if page == 1:
                        return copy.deepcopy(cls.MOCK_LIST_ACTIVE_SUBSCRIBERS_PAGE1)
                    return copy.deepcopy(cls.MOCK_LIST_ACTIVE_SUBSCRIBERS_PAGE2)
                if url.endswith(".json") and "/bounced" not in url \
                        and "/deleted" not in url and "/unconfirmed" not in url \
                        and "/unsubscribed" not in url:
                    return copy.deepcopy(cls.MOCK_LIST_DETAILS)
                if "/bounced.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_BOUNCED_SUBSCRIBERS)
                if "/deleted.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_DELETED_SUBSCRIBERS)
                if "/unconfirmed.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_UNCONFIRMED_SUBSCRIBERS)
                if "/unsubscribed.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_UNSUBSCRIBED_SUBSCRIBERS)

            # client timezone endpoint
            if "/clients/" in url and url.endswith(".json"):
                return {
                    "BasicDetails": {
                        "TimeZone": "(GMT) Coordinated Universal Time"
                    }
                }

            return []

        return mock_fn

    # ------------------------------------------------------------------ #
    #  Start-date mock helpers
    # ------------------------------------------------------------------ #

    MOCK_CAMPAIGN_BOUNCES_RECENT = {
        "Results": [
            {
                "EmailAddress": "recent-bounce@example.com",
                "ListID": "list-001",
                "Date": "2024-07-01 10:00:00",
                "BounceType": "Hard",
                "Reason": "Address rejected",
            },
        ],
        "ResultsOrderedBy": "date",
        "OrderDirection": "asc",
        "PageNumber": 1,
        "PageSize": 1000,
        "RecordsOnThisPage": 1,
        "TotalNumberOfRecords": 1,
        "NumberOfPages": 1,
    }

    @classmethod
    def _create_date_filtering_mock_client(cls):
        """Create a mock client that returns different results based on
        the 'date' param (simulating start_date filtering)."""
        client = MagicMock()
        client.timezone = pytz.UTC
        client.config = dict(cls.default_config)
        client.make_request = MagicMock(
            side_effect=cls._mock_make_request_date_filter())
        return client

    @classmethod
    def _mock_make_request_date_filter(cls):
        """Side-effect that checks for 'date' param on DatePaginated endpoints."""

        def mock_fn(url, method, params=None, body=None):
            date_param = (params or {}).get('date')

            # campaigns parent
            if url.endswith("/campaigns.json"):
                return copy.deepcopy(cls.MOCK_CAMPAIGNS)

            # lists parent
            if url.endswith("/lists.json") and "/lists/" not in url:
                return copy.deepcopy(cls.MOCK_LISTS)

            # campaign child endpoints
            if "/campaigns/" in url:
                if "/bounces.json" in url:
                    # When date filter is present, return only recent data
                    if date_param:
                        return copy.deepcopy(cls.MOCK_CAMPAIGN_BOUNCES_RECENT)
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_BOUNCES)
                if "/summary.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_SUMMARY)
                if "/clicks.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_CLICKS)
                if "/opens.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_OPENS)
                if "/recipients.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_RECIPIENTS)
                if "/spam.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_SPAM_COMPLAINTS)
                if "/unsubscribes.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_UNSUBSCRIBES)
                if "/emailclientusage.json" in url:
                    return copy.deepcopy(cls.MOCK_CAMPAIGN_EMAIL_CLIENT_USAGE)

            # list child endpoints
            if "/lists/" in url:
                if url.endswith(".json") and "/active" not in url and "/bounced" not in url \
                        and "/deleted" not in url and "/unconfirmed" not in url \
                        and "/unsubscribed" not in url:
                    return copy.deepcopy(cls.MOCK_LIST_DETAILS)
                if "/active.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_ACTIVE_SUBSCRIBERS)
                if "/bounced.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_BOUNCED_SUBSCRIBERS)
                if "/deleted.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_DELETED_SUBSCRIBERS)
                if "/unconfirmed.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_UNCONFIRMED_SUBSCRIBERS)
                if "/unsubscribed.json" in url:
                    return copy.deepcopy(cls.MOCK_LIST_UNSUBSCRIBED_SUBSCRIBERS)

            # client timezone endpoint
            if "/clients/" in url and url.endswith(".json"):
                return {
                    "BasicDetails": {
                        "TimeZone": "(GMT) Coordinated Universal Time"
                    }
                }

            return []

        return mock_fn

    @classmethod
    def _run_sync(cls, catalog, state=None, client=None):
        """Run sync using get_streams_to_replicate and the real sync logic."""
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
