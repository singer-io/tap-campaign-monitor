import unittest

from base import CampaignMonitorBaseTest
from tap_tester.base_suite_tests.start_date_test import StartDateTest


class CampaignMonitorStartDateTest(StartDateTest, CampaignMonitorBaseTest):
    """Instantiate start date according to the desired data set and run the
    test."""

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_start_date_test"

    def streams_to_test(self):
        # excluded due to insufficient test data or OAuth scope limitations
        streams_to_exclude = {
            # campaign event streams: 0 records (require real email interactions)
            "campaign_bounces",
            "campaign_clicks",
            "campaign_email_client_usage",
            "campaign_opens",
            "campaign_spam_complaints",
            "campaign_unsubscribes",
            # list streams: OAuth token lacks ManageLists scope (Code 60)
            "lists",
            "list_active_subscribers",
            "list_bounced_subscribers",
            "list_deleted_subscribers",
            "list_details",
            "list_unconfirmed_subscribers",
            "list_unsubscribed_subscribers",
        }
        return self.expected_stream_names().difference(streams_to_exclude)

    @property
    def start_date_1(self):
        return "2015-01-01T00:00:00Z"

    @property
    def start_date_2(self):
        return "2025-09-01T00:00:00Z"

    @unittest.skip("All tested streams have empty REPLICATION_KEYS")
    def test_replication_key_values(self):
        pass

    @unittest.skip("All tested streams have empty REPLICATION_KEYS")
    def test_replicated_records(self):
        pass
