import unittest
from unittest.mock import patch, MagicMock
from parameterized import parameterized


class MockResponse:
    """Class to mock requests.Response object."""
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


class TestCampaignMonitorClientInit(unittest.TestCase):
    """Test CampaignMonitorClient initialization."""

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    def test_init_calls_refresh_and_timezone(self, mock_refresh, mock_tz):
        """Test that __init__ calls refresh_access_token and get_timezone."""
        from tap_campaign_monitor.client import CampaignMonitorClient
        mock_tz.return_value = None
        config = {'client_id': 'test_id', 'refresh_token': 'test_token'}
        client = CampaignMonitorClient(config)
        mock_refresh.assert_called_once()
        mock_tz.assert_called_once()


class TestRefreshAccessToken(unittest.TestCase):
    """Test the refresh_access_token method."""

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    @patch('tap_campaign_monitor.client.requests.request')
    def test_refresh_access_token_success(self, mock_request, mock_tz):
        """Test successful token refresh sets access_token."""
        from tap_campaign_monitor.client import CampaignMonitorClient
        mock_tz.return_value = None
        mock_request.return_value = MockResponse(
            200, {'access_token': 'new_token_123'}
        )
        config = {'client_id': 'test_id', 'refresh_token': 'refresh_123'}
        client = CampaignMonitorClient(config)
        self.assertEqual(client.access_token, 'new_token_123')
        mock_request.assert_called_with(
            "POST",
            "https://api.createsend.com/oauth/token",
            data={'grant_type': 'refresh_token', 'refresh_token': 'refresh_123'}
        )


class TestMakeRequest(unittest.TestCase):
    """Test the make_request method."""

    def _make_client(self):
        """Create a CampaignMonitorClient with mocked init."""
        from tap_campaign_monitor.client import CampaignMonitorClient
        with patch.object(CampaignMonitorClient, 'refresh_access_token'):
            with patch.object(CampaignMonitorClient, 'get_timezone', return_value=None):
                client = CampaignMonitorClient({'client_id': 'test', 'refresh_token': 'tok'})
                client.access_token = 'test_token'
                return client

    @patch('tap_campaign_monitor.client.requests.request')
    def test_successful_request(self, mock_request):
        """Test a successful API request returns JSON."""
        client = self._make_client()
        mock_request.return_value = MockResponse(200, {'data': 'result'})
        result = client.make_request('https://api.example.com/test', 'GET')
        self.assertEqual(result, {'data': 'result'})
        mock_request.assert_called_once_with(
            'GET',
            'https://api.example.com/test',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test_token'
            },
            params=None,
            json=None
        )

    @patch('tap_campaign_monitor.client.time.sleep')
    @patch('tap_campaign_monitor.client.requests.request')
    def test_429_rate_limit_retries(self, mock_request, mock_sleep):
        """Test that 429 status triggers backoff retry."""
        client = self._make_client()
        mock_request.side_effect = [
            MockResponse(429, {}, 'Rate limited'),
            MockResponse(200, {'data': 'ok'})
        ]
        result = client.make_request('https://api.example.com/test', 'GET')
        self.assertEqual(result, {'data': 'ok'})
        mock_sleep.assert_called_once_with(30)
        self.assertEqual(mock_request.call_count, 2)

    @patch('tap_campaign_monitor.client.time.sleep')
    @patch('tap_campaign_monitor.client.requests.request')
    def test_504_gateway_timeout_retries(self, mock_request, mock_sleep):
        """Test that 504 status triggers backoff retry."""
        client = self._make_client()
        mock_request.side_effect = [
            MockResponse(504, {}, 'Gateway Timeout'),
            MockResponse(200, {'data': 'ok'})
        ]
        result = client.make_request('https://api.example.com/test', 'GET')
        self.assertEqual(result, {'data': 'ok'})
        mock_sleep.assert_called_once_with(30)

    @patch('tap_campaign_monitor.client.time.sleep')
    @patch('tap_campaign_monitor.client.requests.request')
    def test_excessive_backoff_raises_error(self, mock_request, mock_sleep):
        """Test that backing off too many times raises RuntimeError."""
        client = self._make_client()
        # Simulate continuous 429 responses — backoff doubles each time:
        # 30 -> 60 -> 120 -> 240 (> 120, so raises)
        mock_request.return_value = MockResponse(429, {}, 'Rate limited')
        with self.assertRaises(RuntimeError) as ctx:
            client.make_request('https://api.example.com/test', 'GET')
        self.assertIn('Backed off too many times', str(ctx.exception))

    @patch('tap_campaign_monitor.client.requests.request')
    def test_non_200_raises_runtime_error(self, mock_request):
        """Test that non-200 non-retryable status raises RuntimeError."""
        client = self._make_client()
        mock_request.return_value = MockResponse(401, {}, 'Unauthorized')
        with self.assertRaises(RuntimeError) as ctx:
            client.make_request('https://api.example.com/test', 'GET')
        self.assertIn('Unauthorized', str(ctx.exception))

    @patch('tap_campaign_monitor.client.requests.request')
    def test_request_with_params_and_body(self, mock_request):
        """Test that params and body are forwarded correctly."""
        client = self._make_client()
        mock_request.return_value = MockResponse(200, {'result': 'ok'})
        params = {'page': 1, 'pagesize': 100}
        body = {'key': 'value'}
        client.make_request('https://api.example.com/test', 'POST',
                            params=params, body=body)
        mock_request.assert_called_once_with(
            'POST',
            'https://api.example.com/test',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test_token'
            },
            params=params,
            json=body
        )


class TestGetTimezone(unittest.TestCase):
    """Test the get_timezone method."""

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.make_request')
    def test_get_timezone_returns_pytz(self, mock_make_request, mock_refresh):
        """Test that get_timezone returns a pytz timezone."""
        from tap_campaign_monitor.client import CampaignMonitorClient
        import pytz

        mock_make_request.return_value = {
            'BasicDetails': {
                'TimeZone': '(GMT-05:00) Eastern Time (US & Canada)'
            }
        }
        config = {'client_id': 'test_id', 'refresh_token': 'test_token'}
        client = CampaignMonitorClient(config)
        self.assertEqual(client.timezone, pytz.timezone('US/Eastern'))

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.make_request')
    def test_get_timezone_unknown_returns_none(self, mock_make_request, mock_refresh):
        """Test unknown timezone string returns None."""
        from tap_campaign_monitor.client import CampaignMonitorClient

        mock_make_request.return_value = {
            'BasicDetails': {
                'TimeZone': 'Unknown Timezone String'
            }
        }
        config = {'client_id': 'test_id', 'refresh_token': 'test_token'}
        client = CampaignMonitorClient(config)
        self.assertIsNone(client.timezone)


if __name__ == '__main__':
    unittest.main()
