import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd
from webapp.app import create_app

class TestUnifiedStockCheck(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('webapp.app.screener.screen_turtle_setups')
    def test_check_stock_dispatch_turtle(self, mock_screen):
        """Test that strategy='turtle' calls the correct screener function."""
        # Setup
        mock_screen.return_value = [{
            "ticker": "AAPL",
            "price": 150.0,
            "signal": "BUY",
            "stop_loss": 140.0
        }]
        
        # Execute
        resp = self.client.get('/screen/check?ticker=AAPL&strategy=turtle')
        
        # Verify
        self.assertEqual(resp.status_code, 200)
        data = resp.json
        self.assertEqual(data['ticker'], 'AAPL')
        mock_screen.assert_called_once()
        self.assertEqual(mock_screen.call_args.kwargs['ticker_list'], ['AAPL'])
        self.assertTrue(mock_screen.call_args.kwargs.get('check_mode'), "check_mode should be True for individual checks")
        # Ensure new fields are attempted to be accessed/returned (mock return value might need update if we strictly test values)
        # But here we mocking the return, so checking the logic of endpoint passing it through is implicit if we get 200.
        # However, to be thorough, let's update mock return to include them and assert.
        
    @patch('webapp.app.screener.screen_turtle_setups')
    def test_check_stock_dispatch_turtle_columns(self, mock_screen):
        mock_screen.return_value = [{
            "ticker": "AAPL",
            "price": 150.0,
            "signal": "BUY",
            "atr": 2.5,
            "52_week_high": 180.0,
            "52_week_low": 120.0
        }]
        resp = self.client.get('/screen/check?ticker=AAPL&strategy=turtle')
        data = resp.json
        self.assertIn('atr', data)
        self.assertIn('52_week_high', data)


    @patch('webapp.app.screener.screen_turtle_setups')
    @patch('webapp.app.screener.screen_hybrid_strategy')
    @patch('webapp.app.screener.screen_trend_followers_isa')
    @patch('webapp.app.screener.screen_mms_ote_setups')
    @patch('webapp.app.screener.screen_5_13_setups')
    @patch('webapp.app.screener.screen_darvas_box')
    @patch('webapp.app.screener.screen_bull_put_spreads')
    def test_check_stock_all_strategies_data_integrity(self, mock_bull, mock_darvas, mock_513, mock_mms, mock_isa, mock_hybrid, mock_turtle):
        """
        Verify that ALL strategies return the unified data fields required for the UI.
        """
        strategies = [
            ('turtle', mock_turtle),
            ('hybrid', mock_hybrid),
            ('isa', mock_isa),
            ('mms', mock_mms),
            ('5/13', mock_513),
            ('darvas', mock_darvas),
            ('bull_put', mock_bull)
        ]
        
        sample_result = [{
            "ticker": "AAPL",
            "price": 150.0,
            "signal": "BUY",
            "atr": 2.5,
            "52_week_high": 180.0,
            "52_week_low": 120.0,
            "sector_change": 1.5,
            "pct_change_1d": 0.5
        }]

        for strat_name, mock_func in strategies:
            # Setup Mock
            mock_func.return_value = sample_result
            
            # Execute
            resp = self.client.get(f'/screen/check?ticker=AAPL&strategy={strat_name}')
            self.assertEqual(resp.status_code, 200, f"Strategy {strat_name} failed")
            
            data = resp.json
            
            # Verify Fields
            required_fields = ['atr', '52_week_high', '52_week_low', 'sector_change', 'price', 'signal']
            for field in required_fields:
                self.assertIn(field, data, f"Strategy {strat_name} missing field {field}")
            
            # Verify Mock Call
            mock_func.assert_called()
            # Reset for next iteration
            mock_func.reset_mock()

    @patch('webapp.app.screener.screen_hybrid_strategy')
    def test_check_stock_hybrid(self, mock_screen):
        """Test that strategy='hybrid' calls the screener with check_mode=True."""
        mock_screen.return_value = [{
            "ticker": "NVDA",
            "price": 400.0,
            "signal": "BUY"
        }]
        
        resp = self.client.get('/screen/check?ticker=NVDA&strategy=hybrid')
        
        self.assertEqual(resp.status_code, 200)
        mock_screen.assert_called_once()
        self.assertEqual(mock_screen.call_args.kwargs['ticker_list'], ['NVDA'])
        self.assertTrue(mock_screen.call_args.kwargs.get('check_mode'), "check_mode must be True for hybrid check")

    @patch('webapp.app.screener.screen_trend_followers_isa')
    def test_check_stock_pnl_calculation(self, mock_screen):
        """Test PnL calculation when entry_price is provided."""
        # Setup
        mock_screen.return_value = [{
            "ticker": "TSLA",
            "price": 200.0,
            "signal": "WAIT"
        }]

        # Execute: Entry 100, Current 200 -> +100 profit (+100%)
        resp = self.client.get('/screen/check?ticker=TSLA&strategy=isa&entry_price=100')

        # Verify
        self.assertEqual(resp.status_code, 200)
        data = resp.json
        self.assertEqual(data['pnl_value'], 100.0)
        self.assertEqual(data['pnl_pct'], 100.0)
        self.assertEqual(data['user_entry_price'], 100.0)

    @patch('webapp.app.screener.screen_trend_followers_isa')
    @patch('webapp.app.yf.download')
    def test_check_stock_historical_entry(self, mock_download, mock_screen):
        """Test fetching historical price when entry_date is provided."""
        # Setup Screener Result
        mock_screen.return_value = [{
            "ticker": "MSFT",
            "price": 300.0,
            "signal": "WAIT"
        }]

        # Setup Historical Price Mock
        # Mocking yf.download to return a DataFrame with a Close price of 250
        # Important: The code expects a Series or a DataFrame where accessing 'Close'
        # works, and then .iloc[0] or .iloc[0,0] gets the value.

        mock_df = pd.DataFrame({'Close': [250.0]})
        mock_download.return_value = mock_df

        # Execute
        resp = self.client.get('/screen/check?ticker=MSFT&strategy=isa&entry_date=2023-01-01')

        # Verify
        self.assertEqual(resp.status_code, 200)
        data = resp.json
        
        # Expected: Entry 250, Current 300 -> +50
        self.assertEqual(data['user_entry_price'], 250.0)
        self.assertEqual(data['pnl_value'], 50.0)
        
        # Verify yf.download called
        mock_download.assert_called_once()
        self.assertEqual(mock_download.call_args.args[0], 'MSFT')

    @patch('webapp.app.screener.screen_trend_followers_isa')
    def test_verdict_isa_exit(self, mock_screen):
        """Test ISA verdict logic: Exit if below trailing stop."""
        mock_screen.return_value = [{
            "ticker": "NVIDIA",
            "price": 100.0,
            "signal": "ENTER",
            "trailing_exit_20d": 110.0 # Price is below stop
        }]

        resp = self.client.get('/screen/check?ticker=NVIDIA&strategy=isa&entry_price=90')
        data = resp.json
        
        # Signal is ENTER (bullish), but price hit stop -> Verdict should be Exit
        self.assertIn("EXIT", data['user_verdict'])
        self.assertIn("Stop Hit", data['user_verdict'])

    @patch('webapp.app.screener.screen_turtle_setups')
    def test_verdict_turtle_hold(self, mock_screen):
        """Test Turtle verdict logic: Hold if above stop."""
        mock_screen.return_value = [{
            "ticker": "AMD",
            "price": 105.0,
            "signal": "BUY",
            "stop_loss": 100.0 # Price above stop
        }]

        resp = self.client.get('/screen/check?ticker=AMD&strategy=turtle&entry_price=90')
        data = resp.json
        
        self.assertIn("HOLD", data['user_verdict'])

if __name__ == '__main__':
    unittest.main()
