import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from decimal import Decimal
import numpy as np

from services import utils
from classes.News import NewsArticle, RelatedArticle


class TestUtils(unittest.TestCase):
    def test_parse_news_article_with_thumbnail(self):
        article = {
            "id": "1",
            "content": {
                "title": "Test Title",
                "summary": "Test Summary",
                "description": "Test Desc",
                "contentType": "news",
                "pubDate": "2024-06-01T12:00:00Z",
                "thumbnail": {
                    "resolutions": [
                        {"url": "url1", "width": 100, "height": 100},
                        {"url": "url2", "width": 50, "height": 50}
                    ]
                },
                "canonicalUrl": {"url": "https://test.com"},
                "provider": {"displayName": "TestProvider"},
                "storyline": {
                    "storylineItems": [
                        {"content": {
                            "title": "Related",
                            "canonicalUrl": {"url": "https://related.com"},
                            "contentType": "news",
                            "provider": {"displayName": "RelProvider"}
                        }}
                    ]
                }
            }
        }
        news = utils.parse_news_article(article)
        self.assertIsInstance(news, NewsArticle)
        self.assertEqual(news.thumbnail_url, "url2")
        self.assertEqual(news.related_articles[0].title, "Related")

    def test_parse_news_article_no_thumbnail(self):
        article = {
            "id": "2",
            "content": {
                "title": "No Thumb",
                "summary": "",
                "description": "",
                "contentType": "news",
                "pubDate": "2024-06-01T12:00:00Z",
                "canonicalUrl": {"url": "https://test.com"},
                "provider": {"displayName": "TestProvider"}
            }
        }
        news = utils.parse_news_article(article)
        self.assertEqual(news.thumbnail_url, "")

    def test_calculate_risk_scores_all(self):
        result = utils.calculate_risk_scores(
            volatility=20, beta=1.5, rsi=70, volume_change=30, debt_to_equity=150, eps=2
        )
        self.assertIn("quant_risk_score", result)
        self.assertTrue(0 <= result["quant_risk_score"] <= 10)

    def test_calculate_risk_scores_negative_eps(self):
        result = utils.calculate_risk_scores(
            volatility=10, beta=1, rsi=50, volume_change=10, debt_to_equity=50, eps=-5
        )
        self.assertGreaterEqual(result["eps_risk"], 7)

    def test_parse_llm_json_response_plain(self):
        data = '{"a": 1, "b": 2}'
        result = utils.parse_llm_json_response(data)
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_parse_llm_json_response_markdown(self):
        data = "```json\n{\"a\": 1, \"b\": 2}\n```"
        result = utils.parse_llm_json_response(data)
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_to_python_type_numpy(self):
        arr = np.array([1])
        self.assertEqual(utils.to_python_type(arr[0]), 1)

    def test_to_python_type_none(self):
        self.assertIsNone(utils.to_python_type(None))

    @patch('services.utils.Stock')
    def test_get_stock_by_ticker_found(self, mock_stock):
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = "stock"
        result = utils.get_stock_by_ticker(db, "TSLA")
        self.assertEqual(result, "stock")

    @patch('services.utils.Stock')
    def test_get_stock_by_ticker_not_found(self, mock_stock):
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        result = utils.get_stock_by_ticker(db, "TSLA")
        self.assertIsNone(result)

    def test_calculate_shallow_risk_score_all(self):
        score = utils.calculate_shallow_risk_score(
            market_cap=5e8, high=200, low=100, pe_ratio=60, eps=-1, debt_to_equity=250, beta=2.5
        )
        self.assertTrue(0 <= score <= 10)

    def test_calculate_shallow_risk_score_no_metrics(self):
        score = utils.calculate_shallow_risk_score()
        self.assertEqual(score, 5.0)

    def test_calculate_shallow_risk(self):
        s = {
            "marketCap": 1e9,
            "fiftyTwoWeekHigh": 200,
            "fiftyTwoWeekLow": 100,
            "forwardPE": 20,
            "epsTrailingTwelveMonths": 2,
            "debtToEquity": 50,
            "beta": 1.1
        }
        score = utils.calculate_shallow_risk(s)
        self.assertTrue(0 <= score <= 10)

    def test_calculate_volume_change_info(self):
        info = {"averageVolume": 100, "regularMarketVolume": 120}
        hist = MagicMock()
        hist.empty = True
        result = utils.calculate_volume_change(hist, info)
        self.assertAlmostEqual(result, 20.0)

    def test_calculate_volume_change_hist(self):
        info = {}
        import pandas as pd
        hist = pd.DataFrame({"Volume": [100, 120, 110, 130, 140, 150, 160]})
        result = utils.calculate_volume_change(hist, info)
        self.assertIsInstance(result, float)

    def test_calculate_volume_change_none(self):
        info = {}
        hist = MagicMock()
        hist.empty = True
        result = utils.calculate_volume_change(hist, info)
        self.assertIsNone(result)
