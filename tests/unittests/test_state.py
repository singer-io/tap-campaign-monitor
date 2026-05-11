import unittest
from tap_campaign_monitor.state import incorporate, get_last_record_value_for_table, save_state, load_state


class TestIncorporate(unittest.TestCase):
    """Test the incorporate function for bookmark state management."""

    def test_incorporate_new_bookmark(self):
        """Test adding a bookmark to an empty state."""
        state = {}
        new_state = incorporate(state, 'my_stream', 'Date', '2024-01-15 10:30:00')
        self.assertIn('bookmarks', new_state)
        self.assertIn('my_stream', new_state['bookmarks'])
        self.assertEqual(new_state['bookmarks']['my_stream']['field'], 'Date')
        self.assertIsNotNone(new_state['bookmarks']['my_stream']['last_record'])

    def test_incorporate_updates_when_newer(self):
        """Test that a newer value updates the bookmark."""
        state = {
            'bookmarks': {
                'my_stream': {
                    'field': 'Date',
                    'last_record': '2024-01-01 00:00:00'
                }
            }
        }
        new_state = incorporate(state, 'my_stream', 'Date', '2024-06-15 12:00:00')
        self.assertEqual(
            new_state['bookmarks']['my_stream']['last_record'],
            '2024-06-15 12:00:00'
        )

    def test_incorporate_does_not_update_when_older(self):
        """Test that an older value does NOT update the bookmark."""
        state = {
            'bookmarks': {
                'my_stream': {
                    'field': 'Date',
                    'last_record': '2024-06-15 12:00:00'
                }
            }
        }
        new_state = incorporate(state, 'my_stream', 'Date', '2024-01-01 00:00:00')
        self.assertEqual(
            new_state['bookmarks']['my_stream']['last_record'],
            '2024-06-15 12:00:00'
        )

    def test_incorporate_none_value_returns_state_unchanged(self):
        """Test that None value returns state unchanged."""
        state = {'bookmarks': {}}
        new_state = incorporate(state, 'my_stream', 'Date', None)
        self.assertEqual(new_state, state)

    def test_incorporate_returns_new_state_dict(self):
        """Test that incorporate returns a new dict (shallow copy)."""
        state = {'bookmarks': {}}
        new_state = incorporate(state, 'my_stream', 'Date', '2024-01-01 00:00:00')
        # incorporate does state.copy() (shallow), so top-level is new
        self.assertIsNot(new_state, state)

    def test_incorporate_composite_key(self):
        """Test incorporate with a composite state key (parent.child)."""
        state = {}
        new_state = incorporate(state, 'campaign123.campaign_bounces', 'Date', '2024-03-01 00:00:00')
        self.assertIn('campaign123.campaign_bounces', new_state['bookmarks'])


class TestGetLastRecordValueForTable(unittest.TestCase):
    """Test the get_last_record_value_for_table function."""

    def test_returns_parsed_date(self):
        """Test that a valid last_record is returned as parsed datetime."""
        state = {
            'bookmarks': {
                'my_stream': {
                    'last_record': '2024-06-15 12:00:00'
                }
            }
        }
        result = get_last_record_value_for_table(state, 'my_stream')
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_returns_none_for_missing_stream(self):
        """Test that None is returned for a stream not in state."""
        state = {'bookmarks': {}}
        result = get_last_record_value_for_table(state, 'missing_stream')
        self.assertIsNone(result)

    def test_returns_none_for_empty_state(self):
        """Test that None is returned for empty state."""
        state = {}
        result = get_last_record_value_for_table(state, 'my_stream')
        self.assertIsNone(result)

    def test_returns_none_when_last_record_is_none(self):
        """Test that None is returned when last_record is None."""
        state = {
            'bookmarks': {
                'my_stream': {
                    'last_record': None
                }
            }
        }
        result = get_last_record_value_for_table(state, 'my_stream')
        self.assertIsNone(result)


class TestSaveState(unittest.TestCase):
    """Test the save_state function."""

    @unittest.mock.patch('tap_campaign_monitor.state.singer.write_state')
    def test_save_state_calls_write_state(self, mock_write_state):
        """Test that save_state calls singer.write_state."""
        state = {'bookmarks': {'stream': {'last_record': '2024-01-01'}}}
        save_state(state)
        mock_write_state.assert_called_once_with(state)

    @unittest.mock.patch('tap_campaign_monitor.state.singer.write_state')
    def test_save_state_empty_does_not_write(self, mock_write_state):
        """Test that save_state with empty/falsy state does not write."""
        save_state({})
        mock_write_state.assert_not_called()
        save_state(None)
        mock_write_state.assert_not_called()


class TestLoadState(unittest.TestCase):
    """Test the load_state function."""

    def test_load_state_none_filename(self):
        """Test that None filename returns empty dict."""
        result = load_state(None)
        self.assertEqual(result, {})

    @unittest.mock.patch('builtins.open',
                         unittest.mock.mock_open(read_data='{"bookmarks": {}}'))
    def test_load_state_valid_file(self):
        """Test loading valid state file."""
        result = load_state('/tmp/state.json')
        self.assertEqual(result, {'bookmarks': {}})

    @unittest.mock.patch('builtins.open',
                         unittest.mock.mock_open(read_data='invalid json'))
    def test_load_state_invalid_json_raises(self):
        """Test that invalid JSON raises RuntimeError."""
        with self.assertRaises(RuntimeError):
            load_state('/tmp/bad_state.json')


if __name__ == '__main__':
    unittest.main()
