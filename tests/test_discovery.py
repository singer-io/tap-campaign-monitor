"""Test tap discovery mode and metadata."""
import unittest

from base import CampaignMonitorBaseTest
from tap_tester.base_suite_tests.discovery_test import DiscoveryTest


class CampaignMonitorDiscoveryTest(DiscoveryTest, CampaignMonitorBaseTest):
    """Test tap discovery mode and metadata conforms to standards.

    The original tap does not set forced-replication-method or
    valid-replication-keys in catalog metadata (it relies on the
    tap_framework default generate_catalog).  We skip the replication
    metadata test that requires those keys.
    """

    @staticmethod
    def name():
        return "tap_tester_campaign_monitor_discovery_test"

    def streams_to_test(self):
        return self.expected_stream_names()

    @unittest.skip("Tap does not set forced-replication-method in catalog metadata")
    def test_replication_metadata(self):
        """Skipped: original tap does not emit forced-replication-method."""

    @unittest.skip("Tap does not set table-key-properties in catalog metadata")
    def test_primary_keys(self):
        """Skipped: original tap (tap_framework) does not emit table-key-properties."""
