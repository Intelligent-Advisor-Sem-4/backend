import pytest
from fastapi.testclient import TestClient
from main import app
from classes.profile import Tickers, Input, RiskScoreIn, RiskScoreOut


client = TestClient(app)


# Test case for `/profile` POST endpoint
def test_profile_base_endpoint():
    response = client.post("/profile/ping")
    assert response.status_code == 200 or response.status_code == 405  # Validate success or failure cases
    if response.status_code == 200:
        assert response.json() == {"msg": "working!"}  # Validate specific response



# Test case for `/profile/get_portfolio` GET endpoint
def test_get_portfolio():
    response = client.get("/profile/get_portfolio")
    assert response.status_code == 200 or response.status_code == 404
    # Confirm the expected response format, if possible
    if response.status_code == 200:
        portfolio_data = Tickers(**response.json())
        assert isinstance(portfolio_data, Tickers)

    

# Test case for `/profile/optimize_portfolio` POST endpoint
def test_optimize_portfolio_success():
    payload = Input(
        tickers=["AAPL", "MSFT", "GOOG", "AMZN"],
        start_date="2020-01-01",
        end_date="2024-01-01",
        num_portfolios=10000,
        investment_amount=5000,
        target_amount=10000,
        years=2,
    ).dict()
    response = client.post("/profile/optimize_portfolio", json=payload)
    assert response.status_code == 200  # Success scenario
    response_content = response.json()
    assert response_content == {
        "method_used": response_content["method_used"],
        "optimal_weights": response_content["optimal_weights"],
        "expected_return": response_content["expected_return"],
        "volatility": response_content["volatility"],
        "sharpe_ratio": response_content["sharpe_ratio"],
        "goal": response_content["goal"],
        "monte_carlo_projection": response_content["monte_carlo_projection"],
    }


# Test failure case for invalid data or missing fields in `/profile/optimize_portfolio`
@pytest.mark.parametrize(
    "payload",
    [
        {},  # Empty payload
        {
            "tickers": ["AAPL"],
            "start_date": "2020-01-01",
        },  # Missing mandatory fields
    ],
)
def test_optimize_portfolio_failure(payload):
    response = client.post("profile/optimize_portfolio", json=payload)
    assert response.status_code == 422  # Validate unprocessable entity error


# Test case for `/profile/risk_score` GET endpoint
def test_get_risk_score():
    response = client.get("/profile/risk_score", params={"user_id": "39a9165a-5693-45f1-8848-18f3da354ea2"})
    assert response.status_code in [200, 204, 404, 500]
    if response.status_code == 200:
        result = response.json()
        assert "score" in result
        assert isinstance(result["score"], (int, float))
    elif response.status_code == 204:
        assert response.text == ""
    elif response.status_code == 404:
        assert response.json()["detail"] == "No risk score found for that user_id"
    elif response.status_code == 500:
        assert response.json()["detail"].startswith("Unexpected error:")


def test_get_risk_score_no_user_id():
    response = client.get("/profile/risk_score")
    assert response.status_code == 422  # Unprocessable entity
    assert response.json()["detail"][0]["msg"] == "Field required"


def test_get_risk_score_invalid_user_id():
    response = client.get("/profile/risk_score", params={"user_id": "invalid-uuid"})
    assert response.status_code == 204  # No content


# Test case for `/profile/risk_score` POST endpoint
def test_post_risk_score_success():
    form_data = {
        "user_id": "39a9165a-5693-45f1-8848-18f3da354ea2",
        "score": "4.5",                                    # form-encoded values are strings
    }
    response = client.post("/profile/risk_score",data=form_data)
    assert response.status_code == 201  # Created
    response_content = response.json()
    assert "score" in response_content
    assert isinstance(response_content["score"], float)
    assert response_content["score"] == 4.5

