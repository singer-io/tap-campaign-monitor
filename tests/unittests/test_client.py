import unittest
from unittest.mock import patch, MagicMock
from parameterized import parameterized


class MockResponse:
    """Class to mock requests.Response object."""
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}

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

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    def test_init_can_skip_timezone(self, mock_refresh, mock_tz):
        """Discovery can authenticate without requesting client details."""
        from tap_campaign_monitor.client import CampaignMonitorClient
        config = {'client_id': 'test_id', 'refresh_token': 'test_token'}

        client = CampaignMonitorClient(config, load_timezone=False)

        mock_refresh.assert_called_once()
        mock_tz.assert_not_called()
        self.assertIsNone(client.timezone)


class TestRefreshAccessToken(unittest.TestCase):
    """Test the refresh_access_token method."""

    @patch('tap_campaign_monitor.client.requests.request')
    def test_refresh_access_token_missing_token_raises_unauthorized(self, mock_request):
        """Test that a missing access_token raises CampaignMonitorUnauthorizedError."""
        from tap_campaign_monitor.client import (
            CampaignMonitorClient, CampaignMonitorUnauthorizedError,
        )
        mock_request.return_value = MockResponse(
            400, {'error': 'invalid_grant', 'error_description': 'Refresh token revoked'}
        )
        config = {'client_id': 'test_id', 'refresh_token': 'bad_token'}
        with self.assertRaises(CampaignMonitorUnauthorizedError) as ctx:
            CampaignMonitorClient(config)
        self.assertIn('401', str(ctx.exception))
        self.assertIn('Refresh token revoked', str(ctx.exception))

    @parameterized.expand([
        (429, 'rate limited', 'Server429Error'),
        (500, 'server error', 'Server5xxError'),
    ])
    @patch('tap_campaign_monitor.client.requests.request')
    def test_refresh_access_token_preserves_transient_error(
            self, status_code, response_text, exception_name, mock_request):
        """Token-service transient failures are not reported as invalid credentials."""
        from tap_campaign_monitor import client as client_module
        from tap_campaign_monitor.client import CampaignMonitorClient
        mock_request.return_value = MockResponse(
            status_code, {'error': 'server_error'}, response_text
        )

        with self.assertRaises(getattr(client_module, exception_name)):
            CampaignMonitorClient(
                {'client_id': 'test_id', 'refresh_token': 'test_token'}
            )

    @patch('tap_campaign_monitor.client.requests.request')
    def test_refresh_access_token_rejects_malformed_success(self, mock_request):
        """A successful response without a token is a response error, not a 401."""
        from tap_campaign_monitor.client import CampaignMonitorClient
        mock_request.return_value = MockResponse(200, {'unexpected': 'value'})

        with self.assertRaisesRegex(RuntimeError, 'access_token is missing'):
            CampaignMonitorClient(
                {'client_id': 'test_id', 'refresh_token': 'test_token'}
            )

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
        mock_sleep.assert_called_once_with(360)
        self.assertEqual(mock_request.call_count, 2)

    @patch('tap_campaign_monitor.client.time.sleep')
    @patch('tap_campaign_monitor.client.requests.request')
    def test_504_gateway_timeout_retries(self, mock_request, mock_sleep):
        """Test that 504 status triggers exponential backoff retry."""
        client = self._make_client()
        mock_request.side_effect = [
            MockResponse(504, {}, 'Gateway Timeout'),
            MockResponse(200, {'data': 'ok'})
        ]
        result = client.make_request('https://api.example.com/test', 'GET')
        self.assertEqual(result, {'data': 'ok'})
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once()

    @patch('tap_campaign_monitor.client.time.sleep')
    @patch('tap_campaign_monitor.client.requests.request')
    def test_excessive_backoff_raises_error(self, mock_request, mock_sleep):
        """Test that backing off too many times raises Server429Error."""
        from tap_campaign_monitor.client import Server429Error
        client = self._make_client()
        mock_request.return_value = MockResponse(429, {}, 'Rate limited')
        with self.assertRaises(Server429Error):
            client.make_request('https://api.example.com/test', 'GET')

    @patch('tap_campaign_monitor.client.requests.request')
    def test_non_200_raises_runtime_error(self, mock_request):
        """Test that non-200 non-retryable status raises RuntimeError."""
        client = self._make_client()
        mock_request.return_value = MockResponse(404, {}, 'Not Found')
        with self.assertRaises(RuntimeError) as ctx:
            client.make_request('https://api.example.com/test', 'GET')
        self.assertIn('Not Found', str(ctx.exception))

    @patch('tap_campaign_monitor.client.requests.request')
    def test_401_raises_unauthorized_error(self, mock_request):
        """Test that 401 raises CampaignMonitorUnauthorizedError with the status code preserved."""
        from tap_campaign_monitor.client import CampaignMonitorUnauthorizedError
        client = self._make_client()
        mock_request.return_value = MockResponse(401, {}, 'Unauthorized')
        with self.assertRaises(CampaignMonitorUnauthorizedError) as ctx:
            client.make_request('https://api.example.com/test', 'GET')
        self.assertIn('401', str(ctx.exception))
        self.assertIn('Unauthorized', str(ctx.exception))

    @patch('tap_campaign_monitor.client.requests.request')
    def test_403_raises_forbidden_error(self, mock_request):
        """Test that 403 raises CampaignMonitorForbiddenError with the status code preserved."""
        from tap_campaign_monitor.client import CampaignMonitorForbiddenError
        client = self._make_client()
        mock_request.return_value = MockResponse(403, {}, 'Forbidden')
        with self.assertRaises(CampaignMonitorForbiddenError) as ctx:
            client.make_request('https://api.example.com/test', 'GET')
        self.assertIn('403', str(ctx.exception))
        self.assertIn('Forbidden', str(ctx.exception))

    @patch('tap_campaign_monitor.client.requests.request')
    def test_401_and_403_raise_distinct_exception_types(self, mock_request):
        """Test that 401 and 403 are not conflated into the same exception type."""
        from tap_campaign_monitor.client import (
            CampaignMonitorForbiddenError, CampaignMonitorUnauthorizedError,
        )
        client = self._make_client()
        self.assertFalse(
            issubclass(CampaignMonitorUnauthorizedError, CampaignMonitorForbiddenError))
        self.assertFalse(
            issubclass(CampaignMonitorForbiddenError, CampaignMonitorUnauthorizedError))

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
