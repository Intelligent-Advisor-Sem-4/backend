import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services import asset_management
from models.models import Stock, AssetStatus
from classes.Asset import Asset, DB_Stock, AssetFastInfo, StockResponse


class TestAssetManagement(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.stock = Stock(
            stock_id=1,
            ticker_symbol="TSLA",
            asset_name="Tesla Inc.",
            currency="USD",
            type="EQUITY",
            exchange="NASDAQ",
            timezone="EST",
            sectorKey="TECH",
            sectorDisp="Technology",
            industryKey="AUTO",
            industryDisp="Auto Manufacturers",
            status=AssetStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            risk_score=5.0,
            risk_score_updated=datetime.now()
        )

    @patch('services.asset_management.yf.Ticker')
    @patch('services.asset_management.send_email_notification')
    def test_create_stock_success(self, mock_email, mock_ticker):
        self.db.query.return_value.filter_by.return_value.first.return_value = None
        mock_fast_info = MagicMock()
        mock_fast_info.shortName = 'Tesla Inc.'
        mock_fast_info.currency = 'USD'
        mock_fast_info.quote_type = 'EQUITY'
        mock_fast_info.exchange = 'NASDAQ'
        mock_fast_info.timezone = 'EST'
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.fast_info = mock_fast_info
        mock_ticker_instance.info = {}
        mock_ticker_instance.history_metadata = {}
        mock_ticker.return_value = mock_ticker_instance

        self.db.add = MagicMock()
        self.db.commit = MagicMock()
        self.db.refresh = MagicMock()

        result = asset_management.create_stock(self.db, "TSLA")
        self.assertIsInstance(result, Stock)
        mock_email.assert_called_once()

    @patch('services.asset_management.yf.Ticker')
    def test_create_stock_already_exists(self, mock_ticker):
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        with self.assertRaises(ValueError):
            asset_management.create_stock(self.db, "TSLA")

    def test_update_stock_status_success(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        self.stock.status = AssetStatus.ACTIVE
        result = asset_management.update_stock_status(self.db, 1, AssetStatus.WARNING)
        self.assertEqual(result.status, AssetStatus.WARNING)

    def test_update_stock_status_pending(self):
        self.stock.status = AssetStatus.PENDING
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        with self.assertRaises(ValueError) as context:
            asset_management.update_stock_status(self.db, 1, AssetStatus.ACTIVE)
        self.assertIn("still pending", str(context.exception))

    def test_update_stock_status_set_pending(self):
        self.stock.status = AssetStatus.ACTIVE
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        with self.assertRaises(ValueError) as context:
            asset_management.update_stock_status(self.db, 1, AssetStatus.PENDING)
        self.assertIn("Cannot set status to PENDING", str(context.exception))

    def test_update_stock_status_not_found(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = None
        with self.assertRaises(ValueError):
            asset_management.update_stock_status(self.db, 1, AssetStatus.ACTIVE)

    def test_update_stock_status_pending(self):
        self.stock.status = AssetStatus.PENDING
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        with self.assertRaises(ValueError):
            asset_management.update_stock_status(self.db, 1, AssetStatus.ACTIVE)

    def test_update_stock_status_set_pending(self):
        self.stock.status = AssetStatus.ACTIVE
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        with self.assertRaises(ValueError):
            asset_management.update_stock_status(self.db, 1, AssetStatus.PENDING)

    def test_get_all_stocks(self):
        self.db.query.return_value.all.return_value = [self.stock]
        result = asset_management.get_all_stocks(self.db)
        self.assertEqual(result, [self.stock])

    @patch('services.asset_management.RiskAnalysis')
    def test_get_db_stocks(self, mock_risk_analysis):
        self.db.query.return_value.offset.return_value.limit.return_value.all.return_value = [self.stock]
        mock_risk_update = MagicMock()
        mock_risk_update.risk_score = 6.5
        mock_risk_analysis.return_value.get_risk_score_and_update.return_value = mock_risk_update

        result = asset_management.get_db_stocks(self.db, 0, 10)
        self.assertIsInstance(result[0], StockResponse)
        self.assertEqual(result[0].risk_score, 6.5)

    def test_get_db_stock_count(self):
        self.db.query.return_value.count.return_value = 5
        result = asset_management.get_db_stock_count(self.db)
        self.assertEqual(result, 5)

    def test_delete_stock_success(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        asset_management.delete_stock(self.db, 1)
        self.db.delete.assert_called_once_with(self.stock)
        self.db.commit.assert_called_once()

    def test_delete_stock_not_found(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = None
        with self.assertRaises(ValueError):
            asset_management.delete_stock(self.db, 999)

    def test_update_stock_risk_score_success(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = self.stock
        result = asset_management.update_stock_risk_score(self.db, 1, 7.5)
        self.assertEqual(result.risk_score, 7.5)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()

    def test_update_stock_risk_score_not_found(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = None
        with self.assertRaises(ValueError):
            asset_management.update_stock_risk_score(self.db, 999, 7.5)

    @patch('services.asset_management.yf.Ticker')
    @patch('services.asset_management.calculate_shallow_risk_score')
    def test_get_asset_by_ticker(self, mock_risk_score, mock_ticker):
        mock_fast_info = MagicMock()
        mock_fast_info.shortName = 'Tesla Inc.'
        mock_fast_info.currency = 'USD'
        mock_fast_info.quote_type = 'EQUITY'
        mock_fast_info.exchange = 'NASDAQ'
        mock_fast_info.last_volume = 1000000

        mock_history_metadata = {'exchangeName': 'NASDAQ', 'shortName': 'Tesla Inc.'}
        # Use a real dict for history_metadata so .get() returns a string

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.fast_info = mock_fast_info
        mock_ticker_instance.info = {
            "marketCap": 1000, "fiftyTwoWeekHigh": 200, "fiftyTwoWeekLow": 100, "forwardPE": 10, "trailingEps": 2,
            "debtToEquity": 0.5, "beta": 1.2
        }
        mock_ticker_instance.history_metadata = mock_history_metadata
        mock_ticker.return_value = mock_ticker_instance
        mock_risk_score.return_value = 5.0
        self.db.query.return_value.filter.return_value.first.return_value = self.stock

        result = asset_management.get_asset_by_ticker(self.db, "TSLA")
        self.assertIsInstance(result, Asset)
        self.assertEqual(result.ticker, "TSLA")