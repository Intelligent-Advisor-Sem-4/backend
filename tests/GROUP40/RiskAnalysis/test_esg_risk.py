import unittest
from unittest.mock import MagicMock
import pandas as pd
from services.risk_analysis.esg_risk import ESGDataService
from classes.Risk_Components import EsgRiskResponse


class TestESGDataService(unittest.TestCase):
    def test_returns_complete_esg_data(self):
        df = pd.DataFrame(
            {0: [12.5, 4.3, 3.8, 4.4]},
            index=['totalEsg', 'environmentScore', 'socialScore', 'governanceScore']
        )
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()

        self.assertIsInstance(result, EsgRiskResponse)
        self.assertEqual(result.total_esg, 12.5)
        self.assertEqual(result.environmental_score, 4.3)
        self.assertEqual(result.social_score, 3.8)
        self.assertEqual(result.governance_score, 4.4)
        self.assertEqual(result.esg_risk_score, 4.5)

    def test_returns_neutral_when_sustainability_is_none(self):
        mock_ticker = MagicMock()
        mock_ticker.sustainability = None

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()

        self.assertIsNone(result.total_esg)
        self.assertIsNone(result.environmental_score)
        self.assertIsNone(result.social_score)
        self.assertIsNone(result.governance_score)
        self.assertEqual(result.esg_risk_score, 5.0)

    def test_returns_neutral_when_sustainability_is_empty(self):
        df = pd.DataFrame()
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()

        self.assertIsNone(result.total_esg)
        self.assertIsNone(result.environmental_score)
        self.assertIsNone(result.social_score)
        self.assertIsNone(result.governance_score)
        self.assertEqual(result.esg_risk_score, 5.0)

    def test_negligible_risk_score_when_total_esg_below_4(self):
        df = pd.DataFrame({0: [3.0]}, index=['totalEsg'])
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertEqual(result.total_esg, 3.0)
        self.assertAlmostEqual(result.esg_risk_score, 1.75)

    def test_low_risk_score_when_total_esg_between_4_and_10(self):
        df = pd.DataFrame({0: [7.5]}, index=['totalEsg'])
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertEqual(result.total_esg, 7.5)
        self.assertAlmostEqual(result.esg_risk_score, 3.17, places=2)

    def test_medium_risk_score_when_total_esg_between_10_and_20(self):
        df = pd.DataFrame({0: [15.0]}, index=['totalEsg'])
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertEqual(result.total_esg, 15.0)
        self.assertAlmostEqual(result.esg_risk_score, 5.0)

    def test_high_risk_score_when_total_esg_between_20_and_30(self):
        df = pd.DataFrame({0: [25.0]}, index=['totalEsg'])
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertEqual(result.total_esg, 25.0)
        self.assertAlmostEqual(result.esg_risk_score, 7.0)

    def test_severe_risk_score_when_total_esg_above_30(self):
        df = pd.DataFrame({0: [40.0]}, index=['totalEsg'])
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertEqual(result.total_esg, 40.0)
        self.assertAlmostEqual(result.esg_risk_score, 9.0)

    def test_caps_risk_score_at_10(self):
        df = pd.DataFrame({0: [100.0]}, index=['totalEsg'])
        mock_ticker = MagicMock()
        mock_ticker.sustainability = df

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertEqual(result.total_esg, 100.0)
        self.assertEqual(result.esg_risk_score, 10.0)

    def test_handles_exception_and_returns_neutral(self):
        mock_ticker = MagicMock()
        type(mock_ticker).sustainability = property(lambda self: (_ for _ in ()).throw(Exception("fail")))

        service = ESGDataService("AAPL", mock_ticker)
        result = service.get_esg_data()
        self.assertIsNone(result.total_esg)
        self.assertEqual(result.esg_risk_score, 5.0)
