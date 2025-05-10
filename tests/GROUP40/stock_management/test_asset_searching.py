import unittest
from unittest.mock import patch, MagicMock
from services.asset_search import yfinance_search
from classes.Search import NewsResponse, QuoteResponse, SearchResult


class TestYFinanceSearch(unittest.TestCase):
    @patch('services.asset_search.yf.Search')
    def test_yfinance_search_basic(self, mock_search):
        # Mock response data
        mock_response = MagicMock()
        mock_response.response = {
            "news": [
                {
                    "uuid": "abc123",
                    "title": "Test News",
                    "publisher": "TestPub",
                    "link": "http://news.com",
                    "providerPublishedTime": "2024-06-01T12:00:00Z",
                    "thumbnail": {
                        "resolutions": [
                            {"url": "url1", "width": 100, "height": 100},
                            {"url": "url2", "width": 50, "height": 50}
                        ]
                    },
                    "relatedTickers": ["AAPL", "TSLA"]
                }
            ],
            "quotes": [
                {
                    "symbol": "AAPL",
                    "shortname": "Apple Inc.",
                    "quoteType": "EQUITY",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "sectorDisplay": "Tech",
                    "industry": "Consumer Electronics",
                    "industryDisplay": "Electronics",
                    "score": 99
                }
            ]
        }
        mock_search.return_value = mock_response

        result = yfinance_search("apple")
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(len(result.news), 1)
        self.assertEqual(len(result.quotes), 1)
        news = result.news[0]
        quote = result.quotes[0]
        self.assertIsInstance(news, NewsResponse)
        self.assertEqual(news.title, "Test News")
        self.assertEqual(news.thumbnail, "url2")  # Smallest resolution
        self.assertEqual(news.relatedTickers, ["AAPL", "TSLA"])
        self.assertIsInstance(quote, QuoteResponse)
        self.assertEqual(quote.symbol, "AAPL")
        self.assertEqual(quote.shortName, "Apple Inc.")
        self.assertEqual(quote.sector, "Technology")

    @patch('services.asset_search.yf.Search')
    def test_yfinance_search_no_news_no_quotes(self, mock_search):
        mock_response = MagicMock()
        mock_response.response = {"news": [], "quotes": []}
        mock_search.return_value = mock_response

        result = yfinance_search("empty")
        self.assertEqual(result.news, [])
        self.assertEqual(result.quotes, [])

    @patch('services.asset_search.yf.Search')
    def test_yfinance_search_news_no_thumbnail(self, mock_search):
        mock_response = MagicMock()
        mock_response.response = {
            "news": [
                {
                    "uuid": "nothumb",
                    "title": "No Thumb",
                    "link": "http://news.com"
                }
            ],
            "quotes": []
        }
        mock_search.return_value = mock_response

        result = yfinance_search("nothumb")
        self.assertIsNone(result.news[0].thumbnail)

    @patch('services.asset_search.yf.Search')
    def test_yfinance_search_quotes_empty_symbol(self, mock_search):
        mock_response = MagicMock()
        mock_response.response = {
            "news": [],
            "quotes": [
                {"symbol": "", "score": 10},
                {"symbol": "TSLA", "score": 5}
            ]
        }
        mock_search.return_value = mock_response

        result = yfinance_search("symbols")
        self.assertEqual(len(result.quotes), 1)
        self.assertEqual(result.quotes[0].symbol, "TSLA")

    @patch('services.asset_search.yf.Search')
    def test_yfinance_search_quotes_sorting_and_limit(self, mock_search):
        mock_response = MagicMock()
        mock_response.response = {
            "news": [],
            "quotes": [
                {"symbol": "A", "score": 1},
                {"symbol": "B", "score": 3},
                {"symbol": "C", "score": 2}
            ]
        }
        mock_search.return_value = mock_response

        result = yfinance_search("sort", quote_count=2)
        self.assertEqual([q.symbol for q in result.quotes], ["B", "C"])

    @patch('services.asset_search.yf.Search')
    def test_processes_news_with_multiple_thumbnails(self, mock_search):
        mock_response = MagicMock()
        mock_response.response = {
            "news": [
                {
                    "uuid": "abc123",
                    "title": "Test News",
                    "thumbnail": {
                        "resolutions": [
                            {"url": "url1", "width": 100, "height": 100},
                            {"url": "url2", "width": 50, "height": 50}
                        ]
                    }
                }
            ],
            "quotes": []
        }
        mock_search.return_value = mock_response

        result = yfinance_search("news")
        self.assertEqual(result.news[0].thumbnail, "url2")