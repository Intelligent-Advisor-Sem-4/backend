import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.models import QuantitativeRiskAnalysis
from services.risk_analysis.quantitative_risk import QuantitativeRiskService
from classes.Risk_Components import QuantRiskResponse, QuantRiskMetrics


class TestQuantitativeRiskService(unittest.TestCase):
    def setUp(self):
        # Mock DB session
        self.mock_db = MagicMock(spec=Session)

        # Mock stock
        self.mock_stock = MagicMock()
        self.mock_stock.stock_id = 1

        # Mock ticker data
        self.mock_ticker_data = MagicMock()
        self.ticker = "AAPL"

        # Create the service with mocks
        self.risk_service = QuantitativeRiskService(
            db=self.mock_db,
            ticker=self.ticker,
            ticker_data=self.mock_ticker_data
        )

        # Replace stock with mock stock
        self.risk_service.stock = self.mock_stock

    def _create_mock_history_data(self):
        """Create mock historical price data"""
        dates = pd.date_range(start=datetime.now() - timedelta(days=60), end=datetime.now(), freq='D')

        # Generate synthetic price data with some volatility
        close_prices = [100.0]
        for _ in range(1, len(dates)):
            # Random daily change between -2% and 2%
            change = np.random.uniform(-0.02, 0.02)
            close_prices.append(close_prices[-1] * (1 + change))

        # Generate synthetic volume data
        volumes = np.random.randint(1000000, 5000000, size=len(dates))

        # Create DataFrame
        data = {
            'Close': close_prices,
            'Volume': volumes
        }

        return pd.DataFrame(data, index=dates)

    def _create_mock_info_data(self):
        """Create mock stock info data"""
        return {
            'beta': 1.2,
            'debtToEquity': 45.2,
            'trailingEps': 5.3,
            'averageVolume': 3000000
        }

    @patch('services.risk_analysis.quantitative_risk.calculate_risk_scores')
    @patch('yfinance.Ticker')
    def test_calculate_quantitative_metrics_success(self, mock_yf_ticker, mock_calculate_risk_scores):
        """Test successful calculation of quantitative metrics"""
        # Setup mock data
        mock_hist = self._create_mock_history_data()
        mock_info = self._create_mock_info_data()

        # Configure mocks
        self.mock_ticker_data.history.return_value = mock_hist
        self.mock_ticker_data.info = mock_info

        mock_yf_ticker.return_value.history.return_value = mock_hist

        # Mock risk scores
        mock_calculate_risk_scores.return_value = {
            "volatility_score": 5.2,
            "beta_score": 4.8,
            "rsi_risk": 6.1,
            "volume_risk": 3.5,
            "debt_risk": 4.0,
            "eps_risk": 2.5,
            "quant_risk_score": 3.42
        }

        # Test with use_llm=False to avoid LLM call
        result = self.risk_service.calculate_quantitative_metrics(lookback_days=30, use_llm=False)

        # Assert the service made proper calls
        self.mock_ticker_data.history.assert_called_once()
        mock_calculate_risk_scores.assert_called_once()

        # Assert response is correct type
        self.assertIsInstance(result, QuantRiskResponse)

        # Check that DB commit was called (for storing data)
        self.mock_db.commit.assert_called_once()

        # Check risk metrics present in result
        self.assertIsInstance(result.risk_metrics, QuantRiskMetrics)
        self.assertLessEqual(result.risk_metrics.quant_risk_score, 3.42)

    def test_store_quantitative_risk_analysis_existing(self):
        """Test updating existing quantitative risk analysis"""
        # Create mock existing analysis
        mock_analysis = MagicMock(spec=QuantitativeRiskAnalysis)
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_analysis

        # Test values
        volatility = 20.5
        beta = 1.3
        rsi = 68.2
        volume_change = 15.3
        debt_to_equity = 42.1
        eps = 4.2
        risk_analysis = {"risk_label": "Moderate Risk", "explanation": "Test explanation"}

        # Call the method
        self.risk_service._store_quantitative_risk_analysis(
            volatility=volatility,
            beta=beta,
            rsi=rsi,
            volume_change=volume_change,
            debt_to_equity=debt_to_equity,
            eps=eps,
            risk_analysis=risk_analysis
        )

        # Verify the existing analysis was updated
        self.assertEqual(mock_analysis.volatility, float(volatility))
        self.assertEqual(mock_analysis.beta, float(beta))
        self.assertEqual(mock_analysis.rsi, float(rsi))
        self.assertEqual(mock_analysis.volume_change, float(volume_change))
        self.assertEqual(mock_analysis.debt_to_equity, float(debt_to_equity))
        self.assertEqual(mock_analysis.eps, float(eps))
        self.assertEqual(mock_analysis.response, risk_analysis)

        # Verify commit was called
        self.mock_db.commit.assert_called_once()

    def test_store_quantitative_risk_analysis_new(self):
        """Test creating new quantitative risk analysis"""
        # Return None to simulate no existing analysis
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None

        # Test values
        volatility = 20.5
        beta = 1.3
        rsi = 68.2
        volume_change = 15.3
        debt_to_equity = 42.1
        eps = 4.2
        risk_analysis = {"risk_label": "Moderate Risk", "explanation": "Test explanation"}

        # Call the method
        self.risk_service._store_quantitative_risk_analysis(
            volatility=volatility,
            beta=beta,
            rsi=rsi,
            volume_change=volume_change,
            debt_to_equity=debt_to_equity,
            eps=eps,
            risk_analysis=risk_analysis
        )

        # Verify a new QuantitativeRiskAnalysis was added to the DB
        self.mock_db.add.assert_called_once()

        # Get the object that was added
        added_analysis = self.mock_db.add.call_args[0][0]
        self.assertIsInstance(added_analysis, QuantitativeRiskAnalysis)
        self.assertEqual(added_analysis.volatility, float(volatility))
        self.assertEqual(added_analysis.beta, float(beta))
        self.assertEqual(added_analysis.stock_id, self.mock_stock.stock_id)

        # Verify commit was called
        self.mock_db.commit.assert_called_once()

    def test_generate_quantitative_risk_explanation_without_llm(self):
        """Test generating risk explanation without using LLM"""
        volatility = 20.5
        beta = 1.3
        rsi = 68.2
        volume_change = 15.3
        debt_to_equity = 42.1
        quant_risk_score = 6.8
        eps = 4.2

        # Call the method with use_llm=False
        result = self.risk_service._generate_quantitative_risk_explanation(
            volatility=volatility,
            beta=beta,
            rsi=rsi,
            volume_change=volume_change,
            debt_to_equity=debt_to_equity,
            quant_risk_score=quant_risk_score,
            eps=eps,
            use_llm=False
        )

        # Verify the result has expected keys
        self.assertIn("risk_label", result)
        self.assertIn("explanation", result)

        # Verify the label is one of the expected values
        valid_labels = ["High Risk", "Moderate Risk", "Slight Risk", "Stable", "Very Stable"]
        self.assertIn(result["risk_label"], valid_labels)

    @patch('services.risk_analysis.quantitative_risk.generate_content_with_llm')
    def test_generate_quantitative_risk_explanation_with_llm(self, mock_generate_content):
        """Test generating risk explanation with LLM"""
        # Mock LLM response
        mock_generate_content.return_value = """
        {
            "risk_label": "Moderate Risk", 
            "explanation": "This is a test explanation from the LLM."
        }
        """

        volatility = 20.5
        beta = 1.3
        rsi = 68.2
        volume_change = 15.3
        debt_to_equity = 42.1
        quant_risk_score = 6.8
        eps = 4.2

        # Call the method with use_llm=True
        result = self.risk_service._generate_quantitative_risk_explanation(
            volatility=volatility,
            beta=beta,
            rsi=rsi,
            volume_change=volume_change,
            debt_to_equity=debt_to_equity,
            quant_risk_score=quant_risk_score,
            eps=eps,
            use_llm=True
        )

        # Verify the generate_content_with_llm was called
        mock_generate_content.assert_called_once()

        # Verify the result has expected keys and values
        self.assertEqual(result["risk_label"], "Moderate Risk")
        self.assertEqual(result["explanation"], "This is a test explanation from the LLM.")

    def test_get_quantitative_metrics_with_existing_recent_analysis(self):
        """Test getting metrics when recent analysis exists"""
        # Create mock existing analysis
        mock_analysis = MagicMock(spec=QuantitativeRiskAnalysis)
        mock_analysis.updated_at = datetime.now() - timedelta(hours=12)  # Less than 1 day old
        mock_analysis.volatility = 20.5
        mock_analysis.beta = 1.3
        mock_analysis.rsi = 68.2
        mock_analysis.volume_change = 15.3
        mock_analysis.debt_to_equity = 42.1
        mock_analysis.eps = 4.2
        mock_analysis.response = {
            "risk_label": "Moderate Risk",
            "explanation": "Existing stored explanation"
        }

        # Configure mock DB to return this analysis
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_analysis

        # Mock risk scores calculation
        with patch('services.risk_analysis.quantitative_risk.calculate_risk_scores') as mock_calculate_risk_scores:
            mock_calculate_risk_scores.return_value = {
                "volatility_score": 5.2,
                "beta_score": 4.8,
                "rsi_risk": 6.1,
                "volume_risk": 3.5,
                "debt_risk": 4.0,
                "eps_risk": 2.5,
                "quant_risk_score": 4.35
            }

            # Call the method
            result = self.risk_service.get_quantitative_metrics(use_llm=False)

            # Verify calculate_risk_scores was called
            mock_calculate_risk_scores.assert_called_once()

            # Verify no new calculation was made
            self.mock_ticker_data.history.assert_not_called()

            # Verify we got the stored explanation
            self.assertEqual(result.risk_label, "Moderate Risk")
            self.assertEqual(result.risk_explanation, "Existing stored explanation")

    @patch('services.risk_analysis.quantitative_risk.QuantitativeRiskService.calculate_quantitative_metrics')
    def test_get_quantitative_metrics_with_outdated_analysis(self, mock_calculate_metrics):
        """Test getting metrics when analysis is outdated"""
        # Create mock outdated analysis
        mock_analysis = MagicMock(spec=QuantitativeRiskAnalysis)
        mock_analysis.updated_at = datetime.now() - timedelta(days=3)  # More than 1 day old

        # Configure mock DB to return this analysis
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_analysis

        # Setup mock calculation result
        mock_result = QuantRiskResponse(
            volatility=22.5,
            beta=1.4,
            rsi=65.2,
            volume_change_percent=18.3,
            debt_to_equity=40.1,
            risk_metrics=QuantRiskMetrics(
                volatility_score=5.5,
                beta_score=4.5,
                rsi_risk=6.0,
                volume_risk=3.2,
                debt_risk=3.8,
                eps_risk=2.2,
                quant_risk_score=4.2
            ),
            risk_label="Slight Risk",
            risk_explanation="New calculated explanation"
        )
        mock_calculate_metrics.return_value = mock_result

        # Call the method
        result = self.risk_service.get_quantitative_metrics(use_llm=False)

        # Verify calculate_quantitative_metrics was called
        mock_calculate_metrics.assert_called_once()

        # Verify we got the new calculation
        self.assertEqual(result.risk_label, "Slight Risk")
        self.assertEqual(result.risk_explanation, "New calculated explanation")

    def test_error_handling_in_calculate_metrics(self):
        """Test error handling in calculate_quantitative_metrics"""
        # Make ticker_data.history raise an exception
        self.mock_ticker_data.history.side_effect = Exception("Test error")

        # Call the method
        result = self.risk_service.calculate_quantitative_metrics()

        # Verify result contains error
        self.assertIn("error", result.model_dump())
        self.assertEqual(result.error, "Test error")
        self.assertEqual(result.risk_metrics.quant_risk_score, 5)  # Default neutral score

    def test_nan_handling_in_get_metrics(self):
        """Test handling of NaN values in database records"""
        # Create mock analysis with NaN values
        mock_analysis = MagicMock(spec=QuantitativeRiskAnalysis)
        mock_analysis.updated_at = datetime.now() - timedelta(hours=12)  # Less than 1 day old
        mock_analysis.volatility = 20.5
        mock_analysis.beta = "nan"  # NaN as string
        mock_analysis.rsi = 68.2
        mock_analysis.volume_change = "nan"  # NaN as string
        mock_analysis.debt_to_equity = 42.1
        mock_analysis.eps = None
        mock_analysis.response = None

        # Configure mock DB to return this analysis
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_analysis

        # Mock risk scores calculation and risk explanation
        with patch('services.risk_analysis.quantitative_risk.calculate_risk_scores') as mock_calculate_risk_scores, \
                patch(
                    'services.risk_analysis.quantitative_risk.QuantitativeRiskService._generate_quantitative_risk_explanation') as mock_generate_explanation:
            mock_calculate_risk_scores.return_value = {
                "volatility_score": 5.2,
                "beta_score": None,  # Should handle None value
                "rsi_risk": 6.1,
                "volume_risk": None,  # Should handle None value
                "debt_risk": 4.0,
                "eps_risk": None,
                "quant_risk_score": 4.35
            }

            mock_generate_explanation.return_value = {
                "risk_label": "Moderate Risk",
                "explanation": "Test explanation with NaN values"
            }

            # Call the method
            result = self.risk_service.get_quantitative_metrics(use_llm=False)

            # Verify NaN handling
            self.assertIsNone(result.beta)
            self.assertIsNone(result.volume_change_percent)

            # Verify risk explanation was called with correct None values
            mock_generate_explanation.assert_called_once_with(
                volatility=20.5,
                beta=None,
                rsi=68.2,
                volume_change=None,
                debt_to_equity=42.1,
                quant_risk_score=4.35,
                eps=None,
                use_llm=False
            )
