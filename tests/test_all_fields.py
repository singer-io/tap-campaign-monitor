from base import CampaignMonitorBaseTest
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest

KNOWN_MISSING_FIELDS = {
}


class CampaignMonitorAllFields(AllFieldsTest, CampaignMonitorBaseTest):
    """Ensure running the tap with all streams and fields selected results in
    the replication of all fields."""

    # ConsentToTrack is in the schema but not returned by the API for some subscribers
    MISSING_FIELDS = {
        "list_active_subscribers": {"ConsentToTrack"},
        "list_deleted_subscribers": {"ConsentToTrack"},
        "list_unsubscribed_subscribers": {"ConsentToTrack"},
    }

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_all_fields_test"

    def streams_to_test(self):
        streams_to_exclude = {
            # campaign event streams: 0 records (require real email interactions)
            "campaign_bounces",
            "campaign_clicks",
            "campaign_email_client_usage",
            "campaign_opens",
            "campaign_spam_complaints",
            "campaign_unsubscribes",
            # list subscriber streams with 0 records in test account
            "list_bounced_subscribers",
            "list_unconfirmed_subscribers",
        }
        return self.expected_stream_names().difference(streams_to_exclude)
