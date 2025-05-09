import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for headless testing (no popup)
import sys
import os
import pytest

# Adjust import path for local module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from explain_portfolio import explain_with_shap, generate_text_explanation

# === Fixtures ===
@pytest.fixture
def dummy_portfolio() -> dict:
    return {
        "optimal_weights": {"AAPL": 0.6, "GOOG": 0.4},
        "expected_return": 0.12,
        "volatility": 0.08,
        "sharpe_ratio": 1.5,
        "goal": "growth",
        "monte_carlo_projection": {
            "expected_final_value": 15000,
            "min_final_value": 10000,
            "max_final_value": 20000,
            "success_rate_percent": 65
        }
    }

# === Unit Tests ===
def test_explain_with_shap_structure(dummy_portfolio):
    result = explain_with_shap(dummy_portfolio)
    
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "shap_contributions" in result, "Missing key: 'shap_contributions'"
    assert "shap_plot_base64" in result, "Missing key: 'shap_plot_base64'"
    assert isinstance(result["shap_contributions"], list), "'shap_contributions' should be a list"
    assert isinstance(result["shap_plot_base64"], str), "'shap_plot_base64' should be a base64 string"
    assert len(result["shap_contributions"]) == len(dummy_portfolio["optimal_weights"]), "Mismatch in number of SHAP contributions"

def test_generate_text_explanation_output(dummy_portfolio):
    shap_data = explain_with_shap(dummy_portfolio)
    explanation = generate_text_explanation(dummy_portfolio, shap_data)
    
    assert isinstance(explanation, str), "Explanation should be a string"
    assert "portfolio" in explanation.lower(), "'portfolio' should appear in explanation"
    
    matched_stocks = [stock for stock in dummy_portfolio["optimal_weights"] if stock in explanation]
    assert matched_stocks, "No stock names from the portfolio appear in the explanation"
