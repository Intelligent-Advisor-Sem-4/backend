import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
from services.portfolio import (
    run_markowitz_optimization,
    simulate_monte_carlo_for_weights,
    build_portfolio_response
)
from classes.profile import Input


class TestPortfolioFunctions(unittest.TestCase):

    def setUp(self):
        # Mock price data for testing
        self.mock_prices = pd.DataFrame({
            'AAPL': [150, 152, 154, 151],
            'GOOG': [2800, 2820, 2835, 2810],
            'SPY': [400, 402, 403, 404]
        })

        self.tickers = ['AAPL', 'GOOG']

        # Mock weights for testing Monte Carlo simulation
        self.mock_weights = {"AAPL": 0.6, "GOOG": 0.4}
        self.mock_mu = pd.Series({'AAPL': 0.1, 'GOOG': 0.12})
        self.mock_cov = pd.DataFrame(
            [[0.0025, 0.0011],
             [0.0011, 0.0036]],
            index=['AAPL', 'GOOG'],
            columns=['AAPL', 'GOOG']
        )

        self.mock_request = Input(
            tickers=['AAPL', 'GOOG'],
            start_date="2022-01-01",
            end_date="2023-01-01",
            investment_amount=100000,
            target_amount=150000,
            years=5
        )

    # ----- TESTS FOR run_markowitz_optimization -----
    @patch("services.portfolio.capm_return")
    @patch("services.portfolio.sample_cov")
    def test_run_markowitz_optimization_valid(self, mock_sample_cov, mock_capm_return):
        # Mock dependencies
        mock_capm_return.return_value = self.mock_mu
        mock_sample_cov.return_value = self.mock_cov

        weights, perf, mu, cov = run_markowitz_optimization(self.mock_prices, self.tickers)

        # Verify outputs
        self.assertTrue(set(weights.keys()) == set(self.tickers))
        self.assertTrue("AAPL" in mu.index and "GOOG" in mu.index)
        self.assertEqual(cov.shape, (2, 2))  # Check covariance matrix size
        self.assertIsInstance(perf, tuple)  # Ensure performance metrics are a tuple

    def test_run_markowitz_optimization_empty_data(self):
        empty_prices = pd.DataFrame()
        with self.assertRaises(KeyError):  # Expects exception due to missing data
            run_markowitz_optimization(empty_prices, self.tickers)

    # ----- TESTS FOR simulate_monte_carlo_for_weights -----
    def test_simulate_monte_carlo_for_weights_valid(self):
        # Perform Monte Carlo simulation
        result = simulate_monte_carlo_for_weights(
            mu=self.mock_mu,
            cov=self.mock_cov,
            weights_dict=self.mock_weights,
            investment_amount=100000,
            target_amount=150000,
            years=5,
            num_simulations=2000
        )

        # Check validity of result
        self.assertIn("expected_final_value", result)
        self.assertIn("min_final_value", result)
        self.assertIn("max_final_value", result)
        self.assertIn("success_rate_percent", result)

        self.assertGreater(result["expected_final_value"], 0)
        self.assertGreaterEqual(result["min_final_value"], 0)
        self.assertGreaterEqual(result["max_final_value"], result["min_final_value"])
        self.assertGreaterEqual(result["success_rate_percent"], 0)

    def test_simulate_monte_carlo_for_weights_with_zero_investment(self):
        result = simulate_monte_carlo_for_weights(
            mu=self.mock_mu,
            cov=self.mock_cov,
            weights_dict=self.mock_weights,
            investment_amount=0,  # Edge case: Zero investment
            target_amount=150000,
            years=5,
            num_simulations=2000
        )
        self.assertEqual(result["expected_final_value"], 0)  # Expected value should be 0
        self.assertEqual(result["success_rate_percent"], 0)  # Success rate must be 0

    # ----- TESTS FOR build_portfolio_response -----
    @patch("services.portfolio.fetch_price_data")
    @patch("services.portfolio.run_markowitz_optimization")
    @patch("services.portfolio.simulate_monte_carlo_for_weights")
    def test_build_portfolio_response(self, mock_simulate_mc, mock_run_markowitz, mock_fetch_data):
        # Mock return values of dependencies
        mock_fetch_data.return_value = self.mock_prices
        mock_run_markowitz.return_value = (
            self.mock_weights,  # Optimal weights
            (0.1, 0.2, 1.5),  # Expected return, Volatility, Sharpe ratio
            self.mock_mu,  # mu
            self.mock_cov  # cov
        )
        mock_simulate_mc.return_value = {
            "expected_final_value": 200000,
            "min_final_value": 150000,
            "max_final_value": 250000,
            "success_rate_percent": 85
        }

        # Execute the function
        self.mock_request.years = 4.5  # Assign a float value to years
        result = build_portfolio_response(self.mock_request)

        # Verify the response structure
        self.assertIn("optimal_weights", result)
        self.assertIn("expected_return", result)
        self.assertIn("volatility", result)
        self.assertIn("sharpe_ratio", result)
        self.assertIn("goal", result)
        self.assertIn("monte_carlo_projection", result)

        # Ensure goal formatting
        self.assertEqual(result["goal"], "$100,000.00 → $150,000.00 in 4.5 year(s)")

    def test_build_portfolio_response_invalid_data(self):
        # Invalid request (e.g., empty tickers)
        invalid_request = Input(
            tickers=[],
            start_date="2022-01-01",
            end_date="2023-01-01",
            investment_amount=100000,
            target_amount=150000,
            years=5
        )
        with self.assertRaises(ValueError):  # Or any specific exception you handle
            build_portfolio_response(invalid_request)


if __name__ == "__main__":
    unittest.main()