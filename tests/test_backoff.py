import unittest
from unittest.mock import patch, MagicMock
import requests
from requests.exceptions import ConnectionError
from tap_campaign_monitor.client import CampaignMonitorClient
from tap_campaign_monitor.client import Server5xxError, Server429Error

class TestCampaignMonitorClient(unittest.TestCase):

    def setUp(self):
        self.config = {
            'refresh_token': 'dummy_refresh',
            'client_id': 'dummy_client'
        }

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_successful_make_request(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request successfully returns the JSON response
        when the HTTP status code is 200.
        Verifies that requests.request is called once with correct parameters.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'ok'}
            mock_request.return_value = mock_response

            result = client.make_request('https://dummy-url.com', 'GET')

            self.assertEqual(result, {'data': 'ok'})
            mock_request.assert_called_once()

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_server_5xx_error_retry(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request raises Server5xxError and retries when
        the response status code is a 5xx server error.
        Verifies that the function retries the request multiple times.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_request.return_value = mock_response

            with self.assertRaises(Server5xxError):
                client.make_request('https://dummy-url.com', 'GET')

            self.assertGreaterEqual(mock_request.call_count, 2)

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_rate_limit_429_retry(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request raises Server429Error and retries when
        the response status code is 429 (rate limit exceeded).
        Verifies that exponential backoff retry logic is triggered.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_request.return_value = mock_response

            with self.assertRaises(Server429Error):
                client.make_request('https://dummy-url.com', 'GET')

            self.assertGreaterEqual(mock_request.call_count, 2)

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_raises_runtime_error_for_other_errors(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request raises RuntimeError for non-retryable HTTP errors,
        such as 400 Bad Request, with the error message propagated.
        Ensures no retries occur for these errors.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_request.return_value = mock_response

            with self.assertRaises(RuntimeError) as context:
                client.make_request('https://dummy-url.com', 'POST')

            self.assertIn("Bad Request", str(context.exception))
            mock_request.assert_called_once()

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_with_params_and_body(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request correctly sends provided query parameters and JSON body
        in the request, and returns the expected JSON response.
        Verifies that the request includes correct headers and payload.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'created'}
            mock_request.return_value = mock_response

            result = client.make_request(
                'https://dummy-url.com',
                'POST',
                params={'a': 'b'},
                body={'x': 'y'}
            )

            self.assertEqual(result, {'status': 'created'})
            mock_request.assert_called_once_with(
                'POST',
                'https://dummy-url.com',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {client.access_token}'
                },
                params={'a': 'b'},
                json={'x': 'y'}
            )

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_eventually_succeeds_after_retry(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request retries on transient 5xx errors and eventually
        succeeds returning the JSON response once a successful status code is received.
        Confirms retry attempts occur before success.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            error_response = MagicMock()
            error_response.status_code = 502

            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {'success': True}

            mock_request.side_effect = [error_response, error_response, success_response]

            result = client.make_request('https://dummy-url.com', 'GET')
            self.assertEqual(result, {'success': True})
            self.assertEqual(mock_request.call_count, 3)

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_max_retries_reached_for_Server429Error(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request raises Server429Error after exceeding maximum retry attempts.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            error_response = MagicMock()
            error_response.status_code = 429

            mock_request.side_effect = [error_response] * 6

            with self.assertRaises(Server429Error):
                client.make_request('https://dummy-url.com', 'GET')
            self.assertEqual(mock_request.call_count, 5)

    @patch('tap_campaign_monitor.client.CampaignMonitorClient.refresh_access_token')
    @patch('tap_campaign_monitor.client.CampaignMonitorClient.get_timezone')
    def test_make_request_max_retries_reached_for_Server5xxError(self, mock_get_timezone, mock_refresh_token):
        """
        Test that make_request raises Server5xxError after exceeding maximum retry attempts.
        """
        mock_get_timezone.return_value = 'UTC'
        mock_refresh_token.return_value = 'dummy_refresh_token'
        client = CampaignMonitorClient(self.config)

        with patch('requests.request') as mock_request:
            error_response = MagicMock()
            error_response.status_code = 500

            mock_request.side_effect = [error_response] * 6

            with self.assertRaises(Server5xxError):
                client.make_request('https://dummy-url.com', 'GET')
            self.assertEqual(mock_request.call_count, 5)
