import unittest
from unittest.mock import patch, MagicMock
from services.asset_screening import run_stock_screen
from classes.ScreenerQueries import ScreenerType

class TestRunStockScreen(unittest.TestCase):
    @patch('services.asset_screening.calculate_shallow_risk')
    @patch('services.asset_screening.Stock')
    @patch('services.asset_screening.yf')
    def test_run_stock_screen_minimal(self, mock_yf, mock_Stock, mock_calc_risk):
        # Mock yfinance screen response
        mock_screen_response = {
            "quotes": [
                {
                    "symbol": "AAPL",
                    "shortName": "Apple Inc.",
                    "regularMarketPrice": 150,
                    "marketCap": 2_000_000_000_000,
                    "averageAnalystRating": "Buy",
                    "dividendYield": 0.006,
                    "forwardPE": 25,
                    "trailingPE": 28,
                    "regularMarketChangePercent": 1.2,
                    "exchange": "NASDAQ",
                    "market": "us_market"
                }
            ],
            "start": 0,
            "count": 1
        }
        mock_yf.PREDEFINED_SCREENER_QUERIES = {
            "most_actives": {
                "query": {},
                "sortField": "marketCap",
                "sortType": "DESC"
            }
        }
        mock_yf.screen.return_value = mock_screen_response

        # Mock risk calculation
        mock_calc_risk.return_value = 7.5

        # Mock DB session and Stock
        mock_db = MagicMock()
        mock_stock_instance = MagicMock()
        mock_stock_instance.ticker_symbol = "AAPL"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_stock_instance]

        # Run
        result = run_stock_screen(
            db=mock_db,
            screen_type=ScreenerType.MOST_ACTIVES,
            offset=0,
            size=1,
            minimal=True
        )

        self.assertIn("quotes", result)
        self.assertEqual(result["quotes"][0]["symbol"], "AAPL")
        self.assertEqual(result["quotes"][0]["risk_score"], 7.5)
        self.assertTrue(result["quotes"][0]["in_db"])
        self.assertEqual(result["start"], 0)
        self.assertEqual(result["count"], 1)

    @patch('services.asset_screening.yf')
    def test_run_stock_screen_invalid_type(self, mock_yf):
        mock_yf.PREDEFINED_SCREENER_QUERIES = {}
        from services.asset_screening import SECTOR_SCREENER_QUERIES
        mock_db = MagicMock()
        with self.assertRaises(ValueError):
            run_stock_screen(
                db=mock_db,
                screen_type=ScreenerType.MOST_ACTIVES,
                offset=0,
                size=1,
                minimal=True
            )

    @patch('services.asset_screening.yf')
    def test_run_stock_screen_custom_query(self, mock_yf):
        mock_yf.screen.return_value = {"quotes": [], "start": 0, "count": 0}
        mock_yf.PREDEFINED_SCREENER_QUERIES = {}
        mock_db = MagicMock()
        custom_query = {"query": {"foo": "bar"}, "sortField": "baz", "sortType": "ASC"}
        result = run_stock_screen(
            db=mock_db,
            screen_type=ScreenerType.CUSTOM,
            custom_query=custom_query,
            minimal=False
        )
        self.assertIn("quotes", result)
        self.assertEqual(result["quotes"], [])