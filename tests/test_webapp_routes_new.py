import pytest
from unittest.mock import patch, MagicMock
from webapp.app import create_app
import json

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

class TestWebappRoutesNew:

    @patch('webapp.app.screener.screen_trend_followers_isa')
    def test_isa_regime_suggestion(self, mock_screen, client):
        # 1. Bearish Market (>50% Sell/Avoid)
        mock_screen.return_value = [
            {'ticker': 'A', 'signal': '❌ SELL/AVOID'},
            {'ticker': 'B', 'signal': '❌ SELL/AVOID'},
            {'ticker': 'C', 'signal': '✅ HOLD'},
        ]

        response = client.get('/screen/isa?region=us_bear') # Unique region key
        assert response.status_code == 200
        data = response.get_json()

        assert 'results' in data
        assert len(data['results']) == 3
        assert 'regime_suggestion' in data
        assert data['regime_suggestion'] is not None
        assert "Market appears Bearish" in data['regime_suggestion']['message']
        assert "Consider using 'Harmonic Cycles'" in data['regime_suggestion']['message']

        # 2. Bullish Market
        mock_screen.return_value = [
            {'ticker': 'A', 'signal': '🚀 ENTER LONG'},
            {'ticker': 'B', 'signal': '✅ HOLD'},
            {'ticker': 'C', 'signal': '❌ SELL/AVOID'},
        ]

        response = client.get('/screen/isa?region=us_bull') # Unique region key
        data = response.get_json()
        assert data['regime_suggestion'] is None

    @patch('webapp.app.screener.screen_fourier_cycles')
    @patch('webapp.app.screener.resolve_ticker')
    def test_fourier_single_ticker(self, mock_resolve, mock_screen, client):
        # Setup
        mock_resolve.return_value = 'AAPL'
        mock_screen.return_value = [{'ticker': 'AAPL', 'signal': 'BUY', 'cycle_position': -0.9}]

        # Test
        response = client.get('/screen/fourier?ticker=AAPL')
        assert response.status_code == 200
        data = response.get_json()

        assert data['ticker'] == 'AAPL'
        assert data['signal'] == 'BUY'

        # Verify call args
        mock_screen.assert_called_with(ticker_list=['AAPL'], time_frame='1d')

    @patch('webapp.app.screener.screen_fourier_cycles')
    def test_fourier_batch(self, mock_screen, client):
        mock_screen.return_value = [{'ticker': 'AAPL'}, {'ticker': 'MSFT'}]

        response = client.get('/screen/fourier')
        assert response.status_code == 200
        data = response.get_json()

        assert isinstance(data, list)
        assert len(data) == 2
