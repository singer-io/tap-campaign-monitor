from tap_tester.base_suite_tests.pagination_test import PaginationTest
from base import CampaignMonitorBaseTest


class CampaignMonitorPaginationTest(PaginationTest, CampaignMonitorBaseTest):
    """
    Ensure tap can replicate multiple pages of data for streams that use pagination.
    """

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_pagination_test"

    def streams_to_test(self):
        # excluded due to insufficient test data or OAuth scope limitations
        streams_to_exclude = {
            # campaign event streams: 0 records
            "campaign_bounces",
            "campaign_clicks",
            "campaign_email_client_usage",
            "campaign_opens",
            "campaign_spam_complaints",
            "campaign_unsubscribes",
            # non-paginating child streams
            "campaign_summary",
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
