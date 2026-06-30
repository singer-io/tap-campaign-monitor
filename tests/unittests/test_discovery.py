import json
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from tap_campaign_monitor.client import CampaignMonitorForbiddenError
from tap_campaign_monitor.streams.campaigns import CampaignsStream
from tap_campaign_monitor.streams.lists import ListsStream
from tap_campaign_monitor.streams.campaign_bounces import CampaignBouncesStream
from tap_campaign_monitor.streams.list_active_subscribers import ListActiveSubscribersStream


CONFIG = {'client_id': 'test_client', 'refresh_token': 'test_token'}
STATE = {}


def _make_args(config=CONFIG, state=STATE):
    args = MagicMock()
    args.config = config
    args.state = state
    return args


def _mock_client():
    client = MagicMock()
    client.config = CONFIG
    return client


class TestCheckAccess(unittest.TestCase):
    """Unit tests for BaseStream.check_access()."""

    def test_child_stream_always_returns_true(self):
        """Child streams bypass access check and return True."""
        client = _mock_client()
        stream = CampaignBouncesStream(CONFIG, STATE, None, client)
        self.assertTrue(stream.check_access())
        client.make_request.assert_not_called()

    def test_parent_stream_accessible(self):
        """Parent stream returns True when API call succeeds."""
        client = _mock_client()
        stream = CampaignsStream(CONFIG, STATE, None, client)
        self.assertTrue(stream.check_access())
        client.make_request.assert_called_once()

    def test_parent_stream_forbidden_403(self):
        """Parent stream returns False when 403 is raised."""
        client = _mock_client()
        client.make_request.side_effect = CampaignMonitorForbiddenError("Forbidden")
        stream = CampaignsStream(CONFIG, STATE, None, client)
        self.assertFalse(stream.check_access())

    def test_parent_stream_forbidden_401(self):
        """Parent stream returns False when 401 (Unauthorized) is raised."""
        client = _mock_client()
        client.make_request.side_effect = CampaignMonitorForbiddenError("Unauthorized")
        stream = CampaignsStream(CONFIG, STATE, None, client)
        self.assertFalse(stream.check_access())


class TestDiscovery(unittest.TestCase):
    """Unit tests for do_discover access control."""

    def _run_discover(self, args, client):
        from tap_campaign_monitor import do_discover
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            do_discover(args, client)
            return json.loads(mock_stdout.getvalue())

    def test_all_streams_accessible_returns_full_catalog(self):
        """All streams returned when all parent streams are accessible."""
        client = _mock_client()
        catalog = self._run_discover(_make_args(), client)
        stream_names = {s['stream'] for s in catalog['streams']}
        self.assertIn('campaigns', stream_names)
        self.assertIn('lists', stream_names)
        self.assertIn('campaign_bounces', stream_names)
        self.assertIn('list_active_subscribers', stream_names)

    def test_inaccessible_parent_excluded_from_catalog(self):
        """campaigns and its children are excluded when campaigns returns 403."""
        client = _mock_client()

        def make_request_side_effect(url, method, *args, **kwargs):
            if '/campaigns' in url:
                raise CampaignMonitorForbiddenError("Forbidden")

        client.make_request.side_effect = make_request_side_effect
        catalog = self._run_discover(_make_args(), client)
        stream_names = {s['stream'] for s in catalog['streams']}
        self.assertNotIn('campaigns', stream_names)
        self.assertNotIn('campaign_bounces', stream_names)
        self.assertIn('lists', stream_names)
        self.assertIn('list_active_subscribers', stream_names)

    def test_all_parents_inaccessible_raises_error(self):
        """Raises CampaignMonitorForbiddenError when no parent stream is accessible."""
        from tap_campaign_monitor import do_discover
        client = _mock_client()
        client.make_request.side_effect = CampaignMonitorForbiddenError("Forbidden")
        with self.assertRaises(CampaignMonitorForbiddenError):
            do_discover(_make_args(), client)

    def test_child_excluded_when_parent_excluded(self):
        """Child streams are excluded when parent is inaccessible."""
        client = _mock_client()

        def make_request_side_effect(url, method, *args, **kwargs):
            if '/lists' in url:
                raise CampaignMonitorForbiddenError("Forbidden")

        client.make_request.side_effect = make_request_side_effect
        catalog = self._run_discover(_make_args(), client)
        stream_names = {s['stream'] for s in catalog['streams']}
        self.assertNotIn('lists', stream_names)
        self.assertNotIn('list_active_subscribers', stream_names)
        self.assertNotIn('list_bounced_subscribers', stream_names)
        self.assertIn('campaigns', stream_names)
        self.assertIn('campaign_bounces', stream_names)


if __name__ == '__main__':
    unittest.main()
