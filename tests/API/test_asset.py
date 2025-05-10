import os
from locale import currency

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from db.dbConnect import get_db

from main import app  # Assuming the FastAPI app is defined in main.py
from tests.API.HEADER import BEARER_TOKEN

# Add the bearer token to the headers
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}"}


# Create a mock DB session to be used by all tests
@pytest.fixture
def mock_db():
    mock_session = MagicMock(spec=Session)
    # Set up the fixture for dependency override
    app.dependency_overrides[get_db] = lambda: mock_session
    yield mock_session
    # Clean up after tests
    app.dependency_overrides.clear()


# Create a test client that will use the overridden dependencies
@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestAssetAPI:
    # Test for the /screen/{screen_type} endpoint
    def test_screen_stocks(self, client, mock_db):
        response = client.get("/assets/screen/technology?offset=0&size=10&minimal=true", headers=HEADERS)
        assert response.status_code == 200
        assert "quotes" in response.json()

    # Test for the /screener-types endpoint
    def test_get_screener_types(self, client):
        response = client.get("/assets/screener-types", headers=HEADERS)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert "technology" in response.json()

    # Test for the /create-stock endpoint
    def test_create_stock(self, client, mock_db):
        # Setup the mock to simulate stock doesn't exist yet
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = None  # Stock doesn't exist yet

        # Mock the add method to simulate adding the stock
        mock_stock = MagicMock()
        mock_stock.stock_id = 123  # Set expected stock ID for the created stock

        # Configure mock to capture the added object and set its stock_id
        def side_effect(added_stock):
            # This is called when db.add() is called in the route handler
            # We set the id of the added stock to simulate DB auto-assigning an ID
            added_stock.stock_id = 123

        mock_db.add.side_effect = side_effect

        response = client.post("/assets/create-stock?ticker=AAPL", headers=HEADERS)
        assert response.status_code == 201  # Expecting success now
        assert response.json()["stock_id"] == 123

    # Test for the /search endpoint
    def test_search(self, client):
        response = client.get("/assets/search?query=Apple&news_count=5&quote_count=3", headers=HEADERS)
        assert response.status_code == 200
        assert "news" in response.json()
        assert "quotes" in response.json()

    # Test for the /{ticker} endpoint
    def test_get_asset(self, client, mock_db):
        # Import necessary modules to patch
        from unittest.mock import patch, MagicMock
        import datetime

        # Mock the Stock model from the database
        mock_stock = MagicMock(
            stock_id=1,
            ticker_symbol="AAPL",
            risk_score=75,
            status="Active",
            risk_score_updated=datetime.datetime.now(),
            # Add any other attributes your Stock model has
        )

        # Setup the mock for db.query().filter().first()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_stock

        # Create mock objects for yf.Ticker
        mock_ticker = MagicMock()

        # Mock the fast_info attribute
        mock_fast_info = MagicMock()
        mock_fast_info.currency = "USD"
        mock_fast_info.exchange = "NMS"
        mock_fast_info.quote_type = "EQUITY"
        mock_fast_info.last_volume = 85000000

        # Set the attributes on the mock Ticker object
        mock_ticker.fast_info = mock_fast_info

        # Mock the history_metadata
        mock_ticker.history_metadata = {
            'shortName': 'Apple Inc.',
            'longName': 'Apple Inc.',
            'exchangeName': 'NASDAQ'
        }

        # Mock the info attribute
        mock_ticker.info = {
            'website': 'https://www.apple.com',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'previousClose': 150.0,
            'open': 151.0,
            'currentPrice': 155.0,
            'dayHigh': 156.0,
            'dayLow': 149.0,
            'averageVolume': 90000000,
            'beta': 1.2,
            'marketCap': 2500000000000,
            'fiftyTwoWeekHigh': 182.0,
            'fiftyTwoWeekLow': 130.0,
            'bid': 154.95,
            'ask': 155.05,
            'trailingEps': 6.15,
            'trailingPE': 25.2,
            'debtToEquity': 150.0,
            'forwardPE': 24.5
        }

        # Mock the calculate_shallow_risk_score function
        with patch('yfinance.Ticker', return_value=mock_ticker), \
                patch('services.asset_management.calculate_shallow_risk_score', return_value=75):
            response = client.get("/assets/AAPL", headers=HEADERS)

            # Assert response status and key data points
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert data["name"] == "Apple Inc."
            assert data["currency"] == "USD"
            assert data["last_price"] == 155.0

            # Verify db was queried with the right filter
            mock_query.filter.assert_called_once()

            # Asset DB info was included
            assert "db" in data
            assert data["db"]["asset_id"] == 1
            assert data["db"]["status"] == "Active"

    # Test for the /fast-info/{ticker} endpoint
    def test_get_asset_fast_info(self, client, mock_db):
        # Setup the mock
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = MagicMock(
            currency="USD",
            prev_close=150.0,
            last_price=155.0
        )

        response = client.get("/assets/fast-info/AAPL", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["currency"] == "USD"

    # Test for the /{stock_id}/status endpoint
    def test_update_status(self, client, mock_db):
        # Setup the mock
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = MagicMock(
            stock_id=1,
            status="Active"
        )

        response = client.put(
            "/assets/1/status",
            json={"status": "Warning"},
            headers=HEADERS
        )

        # Assert the response
        assert response.status_code == 200
        assert response.json()["message"] == "Stock 1 status updated to Warning"

        # Verify the mock was called correctly
        mock_db.query.assert_called()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    # Test for the /{stock_id} DELETE endpoint
    def test_delete_stock(self, client, mock_db):
        # Setup the mock
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = MagicMock(stock_id=1)

        response = client.delete("/assets/1", headers=HEADERS)
        assert response.status_code == 200
        assert "message" in response.json()

    # Test for the /db/stocks endpoint
    def test_get_db_stocks(self, client, mock_db):
        # Setup the mock for the complete query chain: query -> offset -> limit -> all
        mock_query = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        # Configure the chain
        mock_db.query.return_value = mock_query
        mock_query.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit

        # Import datetime for proper date mock values
        from datetime import datetime, timedelta

        # Current time for reference
        now = datetime.now()

        # Set up the return value for the .all() call with proper datetime fields
        mock_stocks = [
            MagicMock(
                stock_id=1,
                ticker_symbol="AAPL",
                asset_name="Apple Inc.",
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(days=1),
                currency="USD",
                risk_score_updated=now - timedelta(days=1),
                status="Active",
                risk_score=65,
            ),
            MagicMock(
                stock_id=2,
                ticker_symbol="GOOGL",
                asset_name="Alphabet Inc.",
                created_at=now - timedelta(days=20),
                currency="USD",
                updated_at=now - timedelta(days=2),
                last_checked=now - timedelta(days=2),
                risk_score_updated=now - timedelta(days=1),
                status="Active",
                risk_score=72,
            )
        ]
        mock_limit.all.return_value = mock_stocks

        response = client.get("/assets/db/stocks?offset=0&limit=2", headers=HEADERS)
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Verify the mocks were called with the correct parameters
        mock_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(2)

    # Test for the /db/stocks/count endpoint
    def test_get_db_stocks_count(self, client, mock_db):
        # Setup the mock
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.count.return_value = 100

        response = client.get("/assets/db/stocks/count", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["count"] == 100
