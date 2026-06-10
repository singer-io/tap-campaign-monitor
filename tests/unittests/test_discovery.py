import json
import unittest
from unittest.mock import MagicMock, patch, call

from tap_campaign_monitor.client import CampaignMonitorForbiddenError
from tap_campaign_monitor.streams import AVAILABLE_STREAMS
from tap_campaign_monitor.streams.campaigns import CampaignsStream
from tap_campaign_monitor.streams.lists import ListsStream
from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
from tap_campaign_monitor.streams.list_active_subscribers import ListActiveSubscribersStream
from tap_campaign_monitor.__init__ import (
    _apply_access_checks,
    _prune_inaccessible_children,
    do_discover,
)


def _make_client(forbidden_tables=None):
    """
    Build a mock CampaignMonitorClient. Calls to make_request raise
    CampaignMonitorForbiddenError for streams whose TABLE is in
    *forbidden_tables*, and return [] otherwise.
    """
    forbidden_tables = forbidden_tables or set()
    client = MagicMock()

    def _make_request_side_effect(url, method, **kwargs):
        for table in forbidden_tables:
            if table in url:
                raise CampaignMonitorForbiddenError("Forbidden")
        return []

    client.make_request.side_effect = _make_request_side_effect
    client.config = {"client_id": "test-client"}
    return client


CONFIG = {"client_id": "test-client", "refresh_token": "test-refresh"}


# ---------------------------------------------------------------------------
# _apply_access_checks
# ---------------------------------------------------------------------------

class TestApplyAccessChecks(unittest.TestCase):
    """Tests for _apply_access_checks()."""

    def test_all_accessible_returns_empty_set(self):
        """When all parent streams respond without 403, no inaccessible set."""
        client = _make_client()
        result = _apply_access_checks(CONFIG, client, AVAILABLE_STREAMS)
        self.assertEqual(result, set())

    def test_campaigns_forbidden_returns_campaigns_in_set(self):
        """When campaigns API returns 403, it appears in inaccessible set."""
        client = _make_client(forbidden_tables={"campaigns"})
        result = _apply_access_checks(CONFIG, client, AVAILABLE_STREAMS)
        self.assertIn("campaigns", result)
        self.assertNotIn("lists", result)

    def test_lists_forbidden_returns_lists_in_set(self):
        """When lists API returns 403, it appears in inaccessible set."""
        client = _make_client(forbidden_tables={"lists"})
        result = _apply_access_checks(CONFIG, client, AVAILABLE_STREAMS)
        self.assertIn("lists", result)
        self.assertNotIn("campaigns", result)

    def test_both_parents_forbidden(self):
        """When both parent streams are forbidden, both appear in set."""
        client = _make_client(forbidden_tables={"campaigns", "lists"})
        result = _apply_access_checks(CONFIG, client, AVAILABLE_STREAMS)
        self.assertIn("campaigns", result)
        self.assertIn("lists", result)

    def test_child_streams_not_checked(self):
        """Child streams (PARENT != '') are never checked directly."""
        client = _make_client()
        result = _apply_access_checks(CONFIG, client, AVAILABLE_STREAMS)
        # Child streams should never appear in inaccessible set from this function
        child_tables = {s.TABLE for s in AVAILABLE_STREAMS if s.PARENT}
        self.assertTrue(child_tables.isdisjoint(result))

    def test_child_streams_do_not_trigger_api_call(self):
        """API calls should only be made for parent streams."""
        client = _make_client()
        _apply_access_checks(CONFIG, client, AVAILABLE_STREAMS)
        # Only parent streams (campaigns, lists) should have been called
        parent_count = sum(1 for s in AVAILABLE_STREAMS if not s.PARENT)
        self.assertEqual(client.make_request.call_count, parent_count)


# ---------------------------------------------------------------------------
# _prune_inaccessible_children
# ---------------------------------------------------------------------------

class TestPruneInaccessibleChildren(unittest.TestCase):
    """Tests for _prune_inaccessible_children()."""

    def test_no_inaccessible_parents_returns_all_streams(self):
        """With no inaccessible parents, all streams are returned."""
        result = _prune_inaccessible_children(AVAILABLE_STREAMS, set())
        self.assertEqual(result, list(AVAILABLE_STREAMS))

    def test_inaccessible_campaigns_removes_campaign_children(self):
        """When campaigns is inaccessible, its children are pruned."""
        result = _prune_inaccessible_children(AVAILABLE_STREAMS, {"campaigns"})
        result_tables = {s.TABLE for s in result}
        # campaigns itself should be gone
        self.assertNotIn("campaigns", result_tables)
        # all campaign_* child streams should be gone
        for stream_cls in AVAILABLE_STREAMS:
            if stream_cls.PARENT == "campaigns":
                self.assertNotIn(stream_cls.TABLE, result_tables)
        # list streams should still be present
        self.assertIn("lists", result_tables)

    def test_inaccessible_lists_removes_list_children(self):
        """When lists is inaccessible, its children are pruned."""
        result = _prune_inaccessible_children(AVAILABLE_STREAMS, {"lists"})
        result_tables = {s.TABLE for s in result}
        self.assertNotIn("lists", result_tables)
        for stream_cls in AVAILABLE_STREAMS:
            if stream_cls.PARENT == "lists":
                self.assertNotIn(stream_cls.TABLE, result_tables)
        self.assertIn("campaigns", result_tables)

    def test_both_parents_inaccessible_returns_empty(self):
        """When both parents are inaccessible, nothing is returned."""
        result = _prune_inaccessible_children(
            AVAILABLE_STREAMS, {"campaigns", "lists"}
        )
        self.assertEqual(result, [])

    def test_accessible_children_are_retained(self):
        """Children of accessible parents should remain in the result."""
        result = _prune_inaccessible_children(AVAILABLE_STREAMS, {"lists"})
        result_tables = {s.TABLE for s in result}
        for stream_cls in AVAILABLE_STREAMS:
            if stream_cls.PARENT == "campaigns":
                self.assertIn(stream_cls.TABLE, result_tables)


# ---------------------------------------------------------------------------
# check_access on BaseStream
# ---------------------------------------------------------------------------

class TestCheckAccess(unittest.TestCase):
    """Tests for BaseStream.check_access()."""

    def test_parent_stream_accessible_returns_true(self):
        """When client does not raise, check_access returns True."""
        client = MagicMock()
        client.make_request.return_value = []
        stream = CampaignsStream(CONFIG, None, None, client)
        self.assertTrue(stream.check_access())

    def test_parent_stream_forbidden_returns_false(self):
        """When client raises CampaignMonitorForbiddenError, check_access returns False."""
        client = MagicMock()
        client.make_request.side_effect = CampaignMonitorForbiddenError("403")
        stream = CampaignsStream(CONFIG, None, None, client)
        self.assertFalse(stream.check_access())

    def test_child_stream_always_returns_true(self):
        """Child streams always return True regardless of API response."""
        client = MagicMock()
        client.make_request.side_effect = CampaignMonitorForbiddenError("403")
        stream = CampaignBouncesStream(CONFIG, None, None, client)
        self.assertTrue(stream.check_access())
        client.make_request.assert_not_called()

    def test_list_stream_accessible_returns_true(self):
        client = MagicMock()
        client.make_request.return_value = []
        stream = ListsStream(CONFIG, None, None, client)
        self.assertTrue(stream.check_access())

    def test_list_child_stream_always_returns_true(self):
        client = MagicMock()
        client.make_request.side_effect = CampaignMonitorForbiddenError("403")
        stream = ListActiveSubscribersStream(CONFIG, None, None, client)
        self.assertTrue(stream.check_access())
        client.make_request.assert_not_called()


# ---------------------------------------------------------------------------
# do_discover
# ---------------------------------------------------------------------------

class TestDoDiscover(unittest.TestCase):
    """Integration-style tests for do_discover()."""

    def _run_discover(self, client):
        """Run do_discover and return the parsed catalog dict."""
        output = []
        with patch("tap_campaign_monitor.__init__.json.dump") as mock_dump:
            mock_dump.side_effect = lambda data, *a, **kw: output.append(data)
            do_discover(client, CONFIG)
        self.assertEqual(len(output), 1)
        return output[0]

    def test_full_access_includes_all_streams(self):
        """All streams appear when credentials have full access."""
        client = _make_client()
        catalog = self._run_discover(client)
        result_tables = {s["tap_stream_id"] for s in catalog["streams"]}
        expected = {s.TABLE for s in AVAILABLE_STREAMS}
        self.assertEqual(result_tables, expected)

    def test_campaigns_forbidden_excludes_campaigns_and_children(self):
        """When campaigns is forbidden, campaigns and its children are excluded."""
        client = _make_client(forbidden_tables={"campaigns"})
        catalog = self._run_discover(client)
        result_tables = {s["tap_stream_id"] for s in catalog["streams"]}
        self.assertNotIn("campaigns", result_tables)
        for stream_cls in AVAILABLE_STREAMS:
            if stream_cls.PARENT == "campaigns":
                self.assertNotIn(stream_cls.TABLE, result_tables)
        # Lists group should still be present
        self.assertIn("lists", result_tables)

    def test_lists_forbidden_excludes_lists_and_children(self):
        """When lists is forbidden, lists and its children are excluded."""
        client = _make_client(forbidden_tables={"lists"})
        catalog = self._run_discover(client)
        result_tables = {s["tap_stream_id"] for s in catalog["streams"]}
        self.assertNotIn("lists", result_tables)
        for stream_cls in AVAILABLE_STREAMS:
            if stream_cls.PARENT == "lists":
                self.assertNotIn(stream_cls.TABLE, result_tables)
        self.assertIn("campaigns", result_tables)

    def test_all_parents_forbidden_raises_exception(self):
        """When no parent stream is accessible, do_discover raises an Exception."""
        client = _make_client(forbidden_tables={"campaigns", "lists"})
        with self.assertRaises(Exception) as ctx:
            do_discover(client, CONFIG)
        self.assertIn("No streams are accessible", str(ctx.exception))

    def test_catalog_entry_structure(self):
        """Each catalog entry has the required Singer catalog keys."""
        client = _make_client()
        catalog = self._run_discover(client)
        for entry in catalog["streams"]:
            self.assertIn("tap_stream_id", entry)
            self.assertIn("stream", entry)
            self.assertIn("key_properties", entry)
            self.assertIn("schema", entry)
            self.assertIn("metadata", entry)

    def test_partial_access_catalog_is_valid_subset(self):
        """Partial access produces a catalog that is a proper subset of full."""
        full_client = _make_client()
        partial_client = _make_client(forbidden_tables={"campaigns"})

        full_catalog = self._run_discover(full_client)
        partial_catalog = self._run_discover(partial_client)

        full_tables = {s["tap_stream_id"] for s in full_catalog["streams"]}
        partial_tables = {s["tap_stream_id"] for s in partial_catalog["streams"]}

        self.assertTrue(partial_tables.issubset(full_tables))
        self.assertLess(len(partial_tables), len(full_tables))
