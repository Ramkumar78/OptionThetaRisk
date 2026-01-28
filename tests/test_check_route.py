
import unittest
from unittest.mock import patch, MagicMock
from webapp.app import create_app

class TestCheckRoute(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('webapp.services.check_service.screener')
    @patch('webapp.blueprints.screener_routes.resolve_ticker')
    def test_check_isa_strategy(self, mock_resolve, mock_screener):
        """Test that ISA check route calls the correct screener and formats result."""
        mock_resolve.return_value = 'AAPL'

        # Mock result from the strategy
        mock_result = {
            'ticker': 'AAPL',
            'price': 150.0,
            'signal': 'ENTER - BUY',
            'trailing_exit_20d': 140.0,
            'verdict': 'BULLISH'
        }
        mock_screener.screen_trend_followers_isa.return_value = [mock_result]

        # Must provide entry_price to trigger user_verdict logic
        response = self.client.get('/screen/check?ticker=AAPL&strategy=isa&entry_price=130')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data['ticker'], 'AAPL')
        # ISA Logic: If curr (150) > trailing_exit (140) and Signal includes ENTER/WATCH -> HOLD
        self.assertEqual(data['user_verdict'], '✅ HOLD (Trend Valid)')

        # Verify call arguments
        mock_resolve.assert_called_once()
        mock_screener.screen_trend_followers_isa.assert_called_once()
        args, kwargs = mock_screener.screen_trend_followers_isa.call_args
        self.assertEqual(kwargs['ticker_list'], ['AAPL'])
        self.assertTrue(kwargs['check_mode'])

    @patch('webapp.services.check_service.screener')
    @patch('webapp.blueprints.screener_routes.resolve_ticker')
    def test_check_turtle_strategy(self, mock_resolve, mock_screener):
        """Test that Turtle check route calls the correct screener and formats result."""
        mock_resolve.return_value = 'TSLA'

        mock_result = {
            'ticker': 'TSLA',
            'price': 200.0,
            'signal': 'BUY',
            'trailing_exit_10d': 190.0,
            'stop_loss': 180.0
        }
        mock_screener.screen_turtle_setups.return_value = [mock_result]

        response = self.client.get('/screen/check?ticker=TSLA&strategy=turtle&entry_price=185')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data['ticker'], 'TSLA')
        # Turtle Logic: if curr (200) > trailing_exit (190) -> HOLD
        self.assertEqual(data['user_verdict'], '✅ HOLD (Trend Valid)')

    @patch('webapp.blueprints.screener_routes.resolve_ticker')
    def test_check_unknown_strategy(self, mock_resolve):
        """Test error handling for unknown strategy."""
        mock_resolve.return_value = 'AAPL'
        response = self.client.get('/screen/check?ticker=AAPL&strategy=unknown_strat')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown strategy", response.get_json()['error'])

if __name__ == '__main__':
    unittest.main()
