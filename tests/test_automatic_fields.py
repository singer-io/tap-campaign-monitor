"""Test that with no fields selected for a stream automatic fields are still
replicated."""
from base import CampaignMonitorBaseTest
from tap_tester.base_suite_tests.automatic_fields_test import MinimumSelectionTest


class CampaignMonitorAutomaticFields(MinimumSelectionTest, CampaignMonitorBaseTest):
    """Test that with no fields selected for a stream automatic fields are
    still replicated."""

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_automatic_fields_test"

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
