from base import CampaignMonitorBaseTest
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest

KNOWN_MISSING_FIELDS = {
}


class CampaignMonitorAllFields(AllFieldsTest, CampaignMonitorBaseTest):
    """Ensure running the tap with all streams and fields selected results in
    the replication of all fields."""

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_all_fields_test"

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
