
import unittest
from unittest.mock import patch
from webapp.app import create_app

class TestWebappRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('webapp.app.screener.screen_hybrid_strategy')
    @patch('webapp.app.get_cached_screener_result')
    def test_screen_hybrid_passes_region_param(self, mock_get_cache, mock_screen_hybrid):
        """
        Regression Test: Ensure that the 'region' query parameter is correctly
        passed from the Flask route to the underlying screener function.
        """
        # mocks
        mock_get_cache.return_value = None # Force cache miss to trigger screener
        mock_screen_hybrid.return_value = [{"ticker": "TEST.L"}] # Dummy result

        # Test UK Region
        response = self.client.get('/screen/hybrid?region=uk&time_frame=1d')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify call args
        # We expect region='uk' to be passed. 
        # Before the fix, this would have failed as region='us' (default) or not passed.
        mock_screen_hybrid.assert_called_once()
        call_args = mock_screen_hybrid.call_args
        
        # Check kwargs
        self.assertIn('region', call_args.kwargs)
        self.assertEqual(call_args.kwargs['region'], 'uk')
        self.assertEqual(call_args.kwargs['time_frame'], '1d')

    @patch('webapp.app.screener.screen_hybrid_strategy')
    @patch('webapp.app.get_cached_screener_result')
    def test_screen_hybrid_defaults_to_us(self, mock_get_cache, mock_screen_hybrid):
        """Verify default behavior is US if no region provided"""
        mock_get_cache.return_value = None
        mock_screen_hybrid.return_value = []

        self.client.get('/screen/hybrid?time_frame=1d')
        
        mock_screen_hybrid.assert_called_once()
        # Default in route is "us"
        self.assertEqual(mock_screen_hybrid.call_args.kwargs['region'], 'us')

if __name__ == '__main__':
    unittest.main()
