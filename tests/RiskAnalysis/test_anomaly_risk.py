import unittest
from unittest.mock import MagicMock
import pandas as pd
from datetime import datetime, timedelta
from services.risk_analysis.anomalies import AnomalyDetectionService
from classes.Risk_Components import AnomalyDetectionResponse, AnomalyFlag, HistoricalDataPoint

class TestAnomalyDetectionService(unittest.TestCase):
    # Reduced day-to-day changes so no anomalies are triggered
    def test_detect_anomalies_with_normal_data(self):
        mock_ticker_data = MagicMock()
        dates = pd.date_range(datetime.now() - timedelta(days=4), periods=5, freq="D")
        data = {
            "Close": [100, 101, 103, 104, 103],
            "Volume": [1000, 1005, 1010, 995, 1002]
        }
        mock_df = pd.DataFrame(data, index=dates)
        mock_ticker_data.history.return_value = mock_df

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        self.assertFalse(response.flags)
        self.assertEqual(len(response.historical_data), 5)

    def test_detect_anomalies_with_empty_data(self):
        mock_ticker_data = MagicMock()
        mock_ticker_data.history.return_value = pd.DataFrame()

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies(lookback_days=5)

        self.assertIsInstance(response, AnomalyDetectionResponse)
        self.assertEqual(response.anomaly_score, 0)
        self.assertEqual(response.flags, [])
        self.assertEqual(response.historical_data, [])

    def test_detect_anomalies_with_big_price_gap(self):
        mock_ticker_data = MagicMock()
        dates = pd.date_range(datetime.now() - timedelta(days=5), periods=5, freq="D")
        data = {
            "Close": [100, 500, 140, 130, 120],  # big jump from 100 to 500
            "Volume": [1000, 1000, 1000, 1000, 1000]
        }
        mock_df = pd.DataFrame(data, index=dates)
        mock_ticker_data.history.return_value = mock_df

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        self.assertTrue(response.flags)
        self.assertEqual(response.flags[0].type, "Price Gap")
        self.assertGreater(response.anomaly_score, 0)

    def test_multiple_flags_increase_anomaly_score(self):
        mock_ticker_data = MagicMock()
        # Create data with large price jumps and volume spikes
        dates = pd.date_range(datetime.now() - timedelta(days=6), periods=6, freq="D")
        data = {
            "Close": [100, 150, 140, 90, 85, 80],  # multiple big changes
            "Volume": [1000, 3000, 1200, 5000, 6000, 7000]
        }
        mock_df = pd.DataFrame(data, index=dates)
        mock_ticker_data.history.return_value = mock_df

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        self.assertIsInstance(response, AnomalyDetectionResponse)
        self.assertTrue(len(response.flags) > 1)
        self.assertTrue(response.anomaly_score > 0)

    def test_detect_anomalies_handles_exceptions(self):
        mock_ticker_data = MagicMock()
        mock_ticker_data.history.side_effect = Exception("Simulated error")

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        self.assertIsInstance(response, AnomalyDetectionResponse)
        self.assertEqual(response.anomaly_score, 0)
        self.assertEqual(response.flags, [])
        self.assertEqual(response.historical_data, [])

if __name__ == "__main__":
    unittest.main()