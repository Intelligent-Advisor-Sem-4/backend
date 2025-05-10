import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from ml_lib.controllers import get_stock_options, get_predictions
from models.models import Stock, AssetStatus, PredictionModel, StockPrediction
from classes.prediction import getpredictprice


class TestPredictionEndpoints(unittest.TestCase):
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
        
        self.prediction_model = PredictionModel(
            model_id=1,
            target_stock_id=1,
            model_version="1.0",
            is_active=True,
            latest_modified_time=datetime.now(),
            rmse=0.5,
            trained_upto_date=datetime.now(),
            data_points=1000
        )

    @patch('ml_lib.controllers.get_stock_options')
    def test_get_active_symbols_success(self, mock_get_stock_options):
        # Mock the response from get_stock_options
        mock_get_stock_options.return_value = [
            {"value": "TSLA", "label": "Tesla Inc."},
            {"value": "AAPL", "label": "Apple Inc."}
        ]
        
        result = get_stock_options()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["value"], "TSLA")
        self.assertEqual(result[1]["value"], "AAPL")

    @patch('ml_lib.controllers.get_stock_options')
    def test_get_active_symbols_empty(self, mock_get_stock_options):
        # Mock empty response
        mock_get_stock_options.return_value = []
        
        result = get_stock_options()
        self.assertEqual(len(result), 0)

    @patch('ml_lib.controllers.get_predictions')
    def test_get_predicted_prices_v2_success(self, mock_get_predictions):
        # Mock the response from get_predictions
        mock_response = {
            "stockData": {
                "ticker": "TSLA",
                "currentPrice": 150.0,
                "priceChange": 2.5,
                "history": [
                    {"date": "2024-03-01", "price": 145.0, "volume": 1000000}
                ]
            },
            "predictionData": {
                "ticker": "TSLA",
                "predictions": [
                    {
                        "date": "2024-03-02",
                        "predicted": 152.0,
                        "confidenceLow": 151.0,
                        "confidenceHigh": 153.0,
                        "change": 1.3
                    }
                ],
                "nextWeek": {
                    "date": "2024-03-08",
                    "predicted": 155.0,
                    "confidenceLow": 154.0,
                    "confidenceHigh": 156.0,
                    "change": 2.0
                }
            },
            "modelMetadata": {
                "modelType": "LSTM Neural Network",
                "version": "1.0",
                "lastUpdated": "2024-03-01",
                "maeScore": 0.5,
                "trainedOn": "2024-02-28",
                "trainingDataPoints": 1000
            }
        }
        mock_get_predictions.return_value = mock_response

        # Create test data
        test_data = getpredictprice(
            ticker_symbol="TSLA",
            starting_date="2024-03-01",
            ending_date="2024-03-08"
        )

        result = get_predictions(
            test_data.ticker_symbol,
            test_data.starting_date,
            test_data.ending_date
        )

        self.assertEqual(result["stockData"]["ticker"], "TSLA")
        self.assertEqual(len(result["predictionData"]["predictions"]), 1)
        self.assertEqual(result["modelMetadata"]["modelType"], "LSTM Neural Network")

    @patch('ml_lib.controllers.get_predictions')
    def test_get_predicted_prices_v2_error(self, mock_get_predictions):
        # Mock error response
        mock_get_predictions.return_value = {"error": "Stock not found"}

        test_data = getpredictprice(
            ticker_symbol="INVALID",
            starting_date="2024-03-01",
            ending_date="2024-03-08"
        )

        result = get_predictions(
            test_data.ticker_symbol,
            test_data.starting_date,
            test_data.ending_date
        )

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Stock not found")


if __name__ == '__main__':
    unittest.main() 