import unittest

from base import CampaignMonitorBaseTest
from tap_tester.base_suite_tests.bookmark_test import BookmarkTest


class CampaignMonitorBookmarkTest(BookmarkTest, CampaignMonitorBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""
    bookmark_format = "%Y-%m-%d %H:%M:%S"
    initial_bookmarks = {}

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_bookmark_test"

    def streams_to_test(self):
        # excluded: full_table streams with no data, and streams with OAuth scope issues
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

    @unittest.skip("All tested streams are FULL_TABLE and do not write bookmark entries to state")
    def test_syncs_were_successful(self):
        pass
