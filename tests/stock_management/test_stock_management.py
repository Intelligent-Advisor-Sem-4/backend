import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from services.asset_management import (
    create_stock, update_stock_status, get_all_stocks, get_db_stocks,
    get_db_stock_count, delete_stock, update_stock_risk_score,
    get_asset_by_ticker, get_asset_by_ticker_fast
)
from models.models import Stock, AssetStatus
from classes.Asset import Asset, DB_Stock, AssetFastInfo, StockResponse
from tests.test_db_session import get_test_db


class TestAssetManagement(unittest.TestCase):
    def setUp(self):
        # Create a mock session for most tests
        self.db = MagicMock(spec=Session)

        # Create a mock Stock object for testing
        self.mock_stock = MagicMock(spec=Stock)
        self.mock_stock.stock_id = 1
        self.mock_stock.ticker_symbol = "TSLA"
        self.mock_stock.asset_name = "Tesla Inc."
        self.mock_stock.currency = "USD"
        self.mock_stock.type = "EQUITY"
        self.mock_stock.exchange = "NMS"
        self.mock_stock.timezone = "America/New_York"
        self.mock_stock.sectorKey = "technology"
        self.mock_stock.sectorDisp = "Technology"
        self.mock_stock.industryKey = "auto"
        self.mock_stock.industryDisp = "Auto Manufacturers"
        self.mock_stock.status = AssetStatus.ACTIVE
        self.mock_stock.risk_score = 6.5
        self.mock_stock.risk_score_updated = datetime.now()
        self.mock_stock.created_at = datetime.now()
        self.mock_stock.updated_at = datetime.now()

        # Get a real db session for integration tests
        self.real_db = get_test_db()

    def tearDown(self):
        # Close the real db session
        if hasattr(self, 'real_db'):
            self.real_db.close()

    @patch('services.asset_management.yf.Ticker')
    @patch('services.asset_management.send_email_notification')
    def test_create_stock(self, mock_send_email, mock_ticker):
        # Setup mock Ticker response
        mock_fast_info = MagicMock()
        mock_fast_info.shortName = "Tesla Inc."
        mock_fast_info.currency = "USD"
        mock_fast_info.quote_type = "EQUITY"
        mock_fast_info.exchange = "NMS"
        mock_fast_info.timezone = "America/New_York"

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.fast_info = mock_fast_info
        mock_ticker_instance.info = {
            "sectorKey": "technology",
            "sectorDisp": "Technology",
            "industryKey": "auto",
            "industryDisp": "Auto Manufacturers"
        }
        mock_ticker_instance.history_metadata = {}

        mock_ticker.return_value = mock_ticker_instance

        # Mock query to check if stock exists
        self.db.query.return_value.filter_by.return_value.first.return_value = None

        # Call the function
        result = create_stock(self.db, "TSLA")

        # Assertions
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        mock_send_email.assert_called_once()
        self.assertEqual(result, self.db.refresh.return_value)

    def test_update_stock_status(self):
        # Mock query to find the stock
        self.db.query.return_value.filter_by.return_value.first.return_value = self.mock_stock

        # Set stock as active so it can be updated
        self.mock_stock.status = AssetStatus.ACTIVE

        # Call the function
        result = update_stock_status(self.db, 1, AssetStatus.WARNING)

        # Assertions
        self.assertEqual(self.mock_stock.status, AssetStatus.WARNING)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        self.assertEqual(result, self.mock_stock)

        # Test for pending status (should raise error)
        with self.assertRaises(ValueError):
            self.mock_stock.status = AssetStatus.PENDING
            update_stock_status(self.db, 1, AssetStatus.WARNING)

        # Test for setting status to pending (should raise error)
        with self.assertRaises(ValueError):
            self.mock_stock.status = AssetStatus.ACTIVE
            update_stock_status(self.db, 1, AssetStatus.PENDING)

    def test_get_all_stocks(self):
        # Mock query to return all stocks
        self.db.query.return_value.all.return_value = [self.mock_stock]

        # Call the function
        result = get_all_stocks(self.db)

        # Assertions
        self.assertEqual(result, [self.mock_stock])

    @patch('services.asset_management.RiskAnalysis')
    def test_get_db_stocks(self, mock_risk_analysis):
        # Setup mock risk analysis response
        mock_risk_update = MagicMock()
        mock_risk_update.risk_score = 6.5
        mock_analyser = MagicMock()
        mock_analyser.get_risk_score_and_update.return_value = mock_risk_update
        mock_risk_analysis.return_value = mock_analyser

        # Mock query to return stocks with pagination
        self.db.query.return_value.offset.return_value.limit.return_value.all.return_value = [self.mock_stock]

        # Call the function
        result = get_db_stocks(self.db, 0, 10)

        # Assertions
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], StockResponse)
        self.assertEqual(result[0].ticker_symbol, "TSLA")
        self.assertEqual(result[0].risk_score, 6.5)

    def test_get_db_stock_count(self):
        # Mock query to return count
        self.db.query.return_value.count.return_value = 5

        # Call the function
        result = get_db_stock_count(self.db)

        # Assertions
        self.assertEqual(result, 5)

    def test_delete_stock(self):
        # Mock query to find the stock
        self.db.query.return_value.filter_by.return_value.first.return_value = self.mock_stock

        # Call the function
        delete_stock(self.db, 1)

        # Assertions
        self.db.delete.assert_called_once_with(self.mock_stock)
        self.db.commit.assert_called_once()

        # Test for non-existent stock
        self.db.query.return_value.filter_by.return_value.first.return_value = None
        with self.assertRaises(ValueError):
            delete_stock(self.db, 999)

    def test_update_stock_risk_score(self):
        # Mock query to find the stock
        self.db.query.return_value.filter_by.return_value.first.return_value = self.mock_stock

        # Call the function
        result = update_stock_risk_score(self.db, 1, 7.5)

        # Assertions
        self.assertEqual(self.mock_stock.risk_score, 7.5)
        self.assertIsNotNone(self.mock_stock.risk_score_updated)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        self.assertEqual(result, self.mock_stock)

    @patch('services.asset_management.yf.Ticker')
    @patch('services.asset_management.calculate_shallow_risk_score')
    def test_get_asset_by_ticker(self, mock_risk_score, mock_ticker):
        # Setup mock Ticker response
        mock_fast_info = MagicMock()
        mock_fast_info.shortName = "Tesla Inc."
        mock_fast_info.currency = "USD"
        mock_fast_info.quote_type = "EQUITY"
        mock_fast_info.exchange = "NMS"
        mock_fast_info.last_volume = 10000000

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.fast_info = mock_fast_info
        mock_ticker_instance.info = {
            "sector": "Technology",
            "industry": "Auto Manufacturers",
            "previousClose": 200.0,
            "open": 205.0,
            "currentPrice": 210.0,
            "dayHigh": 215.0,
            "dayLow": 200.0,
            "averageVolume": 15000000,
            "beta": 1.5,
            "marketCap": 700000000000,
            "fiftyTwoWeekHigh": 400.0,
            "fiftyTwoWeekLow": 150.0,
            "bid": 210.0,
            "ask": 211.0,
            "trailingEps": 4.5,
            "trailingPE": 46.67
        }
        mock_ticker_instance.history_metadata = {
            "exchangeName": "NASDAQ"
        }

        mock_ticker.return_value = mock_ticker_instance

        # Mock risk score calculation
        mock_risk_score.return_value = 6.5

        # Mock query to find the stock in DB
        self.db.query.return_value.filter.return_value.first.return_value = self.mock_stock

        # Call the function
        result = get_asset_by_ticker(self.db, "TSLA")

        # Assertions
        self.assertIsInstance(result, Asset)
        self.assertEqual(result.ticker, "TSLA")
        self.assertEqual(result.name, "Tesla Inc.")
        self.assertEqual(result.exchange, "NASDAQ")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.market_cap, 700000000000)
        self.assertIsInstance(result.db, DB_Stock)
        self.assertTrue(result.db.in_db)
        self.assertEqual(result.db.risk_score, 6.5)

    @patch('services.asset_management.yf.Ticker')
    def test_get_asset_by_ticker_fast(self, mock_ticker):
        # Setup mock Ticker response
        mock_fast_info = MagicMock()
        mock_fast_info.currency = "USD"
        mock_fast_info.previous_close = 200.0
        mock_fast_info.last_price = 210.0

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.fast_info = mock_fast_info
        mock_ticker.return_value = mock_ticker_instance

        # Call the function
        result = get_asset_by_ticker_fast(self.db, "TSLA")

        # Assertions
        self.assertIsInstance(result, AssetFastInfo)
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.prev_close, 200.0)
        self.assertEqual(result.last_price, 210.0)

    # Integration tests using real database

    def test_integration_get_all_stocks(self):
        # This test uses the real database connection
        try:
            stocks = get_all_stocks(self.real_db)
            self.assertIsInstance(stocks, list)
            # Check that result is a list of Stock objects
            if stocks:
                self.assertIsInstance(stocks[0], Stock)
        except Exception as e:
            self.fail(f"Integration test failed with error: {str(e)}")

    def test_integration_get_db_stock_count(self):
        # This test uses the real database connection
        try:
            count = get_db_stock_count(self.real_db)
            self.assertIsInstance(count, int)
            self.assertGreaterEqual(count, 0)
        except Exception as e:
            self.fail(f"Integration test failed with error: {str(e)}")

    @patch('services.asset_management.RiskAnalysis')
    def test_integration_get_db_stocks(self, mock_risk_analysis):
        # Setup mock risk analysis response for integration test
        mock_risk_update = MagicMock()
        mock_risk_update.risk_score = 6.5
        mock_analyser = MagicMock()
        mock_analyser.get_risk_score_and_update.return_value = mock_risk_update
        mock_risk_analysis.return_value = mock_analyser

        try:
            stocks = get_db_stocks(self.real_db, 0, 10)
            self.assertIsInstance(stocks, list)
            # If there are stocks in the database, validate response
            if stocks:
                self.assertIsInstance(stocks[0], StockResponse)
        except Exception as e:
            self.fail(f"Integration test failed with error: {str(e)}")


if __name__ == "__main__":
    unittest.main()
