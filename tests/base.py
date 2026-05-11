import os
import unittest

from tap_tester import connections, menagerie, runner
from tap_tester.logger import LOGGER
from tap_tester.base_suite_tests.base_case import BaseCase


class CampaignMonitorBaseTest(BaseCase):
    """Setup expectations for test sub classes.

    Metadata describing streams. A bunch of shared methods that are used
    in tap-tester tests. Shared tap-specific methods (as needed).
    """
    start_date = "2019-01-01T00:00:00Z"

    @staticmethod
    def tap_name():
        """The name of the tap."""
        return "tap-campaign-monitor"

    @staticmethod
    def get_type():
        """The expected url route ending."""
        return "platform.campaign-monitor"

    @classmethod
    def expected_metadata(cls):
        """The expected streams and metadata about the streams.

        Campaign Monitor uses two parent streams (campaigns, lists) and
        several child streams.  The DatePaginatedChildStream children use
        date-based bookmarks (incremental-like), while other children
        and parents are full-table.

        NOTE: The tap itself does NOT set forced-replication-method in
        catalog metadata.  We declare FULL_TABLE here so tap-tester
        skips incremental-specific assertions for streams that don't
        use bookmarks.
        """
        return {
            "campaigns": {
                cls.PRIMARY_KEYS: {"CampaignID"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_bounces": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_clicks": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_email_client_usage": {
                cls.PRIMARY_KEYS: {"CampaignID", "Client", "Version"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_opens": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_recipients": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_spam_complaints": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_summary": {
                cls.PRIMARY_KEYS: {"CampaignID"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "campaign_unsubscribes": {
                cls.PRIMARY_KEYS: {"CampaignID", "ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "lists": {
                cls.PRIMARY_KEYS: {"ListID"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "list_active_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "list_bounced_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "list_deleted_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "list_details": {
                cls.PRIMARY_KEYS: {"ListID"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "list_unconfirmed_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
            "list_unsubscribed_subscribers": {
                cls.PRIMARY_KEYS: {"ListID", "EmailAddress", "Date"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.RESPECTS_START_DATE: False,
                cls.API_LIMIT: 1,
            },
        }

    @staticmethod
    def get_credentials():
        """Authentication information for the test account."""
        return {
            'client_id': os.getenv('TAP_CAMPAIGN_MONITOR_CLIENT_ID'),
            'refresh_token': os.getenv('TAP_CAMPAIGN_MONITOR_REFRESH_TOKEN'),
        }

    def get_properties(self, original: bool = True):
        """Configuration of properties required for the tap."""
        return {
            'client_id': os.getenv('TAP_CAMPAIGN_MONITOR_CLIENT_ID'),
            'refresh_token': os.getenv('TAP_CAMPAIGN_MONITOR_REFRESH_TOKEN'),
        }
