import unittest
from unittest.mock import MagicMock
import pandas as pd
from datetime import datetime, timedelta
from services.risk_analysis.anomalies import AnomalyDetectionService
from classes.Risk_Components import AnomalyDetectionResponse, AnomalyFlag, HistoricalDataPoint


class TestAnomalyDetectionService(unittest.TestCase):
    # Tests normal price movements with no anomalies expected
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
        self.assertEqual(response.anomaly_score, 0)

    # Tests handling of empty datasets
    def test_detect_anomalies_with_empty_data(self):
        mock_ticker_data = MagicMock()
        mock_ticker_data.history.return_value = pd.DataFrame()

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies(lookback_days=5)

        self.assertIsInstance(response, AnomalyDetectionResponse)
        self.assertEqual(response.anomaly_score, 0)
        self.assertEqual(response.flags, [])
        self.assertEqual(response.historical_data, [])

    # Tests detection of a large price gap (400%)
    def test_detect_anomalies_with_big_price_gap(self):
        mock_ticker_data = MagicMock()
        dates = pd.date_range(datetime.now() - timedelta(days=4), periods=5, freq="D")
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
        self.assertIn("Major price change", response.flags[0].description)
        self.assertEqual(len(response.flags), 2)  # Should detect both the 400% increase and the -72% decrease
        self.assertGreater(response.anomaly_score, 0)

    # Tests detection of moderate price changes
    def test_detect_moderate_price_changes(self):
        mock_ticker_data = MagicMock()
        dates = pd.date_range(datetime.now() - timedelta(days=19), periods=20, freq="D")
        # Create stable prices with one moderate anomaly
        prices = [100] * 10 + [100, 110, 108, 109, 110, 109, 108, 107, 106, 105]
        data = {
            "Close": prices,
            "Volume": [1000] * 20
        }
        mock_df = pd.DataFrame(data, index=dates)
        mock_ticker_data.history.return_value = mock_df

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        # Should detect the 10% change as statistical anomaly
        self.assertTrue(response.flags)
        self.assertEqual(response.flags[0].type, "Price Gap")
        self.assertIn("Statistically unusual", response.flags[0].description)

    # Tests that multiple anomalies increase the overall score
    def test_multiple_flags_increase_anomaly_score(self):
        mock_ticker_data = MagicMock()
        # Create data with large price jumps and volume spikes
        dates = pd.date_range(datetime.now() - timedelta(days=5), periods=6, freq="D")
        data = {
            "Close": [100, 150, 140, 90, 85, 80],  # multiple big changes
            "Volume": [1000, 3000, 1200, 5000, 6000, 7000]
        }
        mock_df = pd.DataFrame(data, index=dates)
        mock_ticker_data.history.return_value = mock_df

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        self.assertIsInstance(response, AnomalyDetectionResponse)
        # Should detect at least 3 price gaps and 3 volume spikes
        self.assertTrue(len(response.flags) >= 6)

        # Find anomaly score and ensure it's higher due to multiple flags
        base_score = max([flag.severity for flag in response.flags])
        self.assertTrue(response.anomaly_score > base_score)

    # Tests detection of bearish patterns
    def test_detect_bearish_pattern(self):
        mock_ticker_data = MagicMock()
        dates = pd.date_range(datetime.now() - timedelta(days=4), periods=5, freq="D")
        data = {
            "Close": [100, 99, 97, 94, 90],  # 5 consecutive down days
            "Volume": [1000, 1000, 1000, 1000, 1000]
        }
        mock_df = pd.DataFrame(data, index=dates)
        mock_ticker_data.history.return_value = mock_df

        service = AnomalyDetectionService("FAKE", mock_ticker_data)
        response = service.detect_anomalies()

        self.assertTrue(any(flag.type == "Bearish Pattern" for flag in response.flags))

    # Tests exception handling
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
