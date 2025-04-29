from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
from typing import AsyncGenerator

from db.dbConnect import get_db
from services.risk_analysis.analyser import RiskAnalysis

router = APIRouter(prefix="/risk-analysis", tags=["risk-analysis"])


async def risk_analysis_stream(ticker: str, lookback_days: int, db: Session) -> AsyncGenerator[str, None]:
    """Generate streaming risk analysis data"""
    try:
        analyzer = RiskAnalysis(ticker=ticker, db=db)

        # Step 1: Send news articles
        news_articles = analyzer.get_news()
        yield f"data: {json.dumps({'type': 'news_articles', 'data': [article.dict() for article in news_articles]})}\n\n"
        await asyncio.sleep(0.1)  # Small delay between messages

        # Step 2: Send news sentiment report
        news_sentiment = analyzer.get_news_sentiment_risk(prefer_newest=True)
        yield f"data: {json.dumps({'type': 'news_sentiment', 'data': news_sentiment})}\n\n"
        await asyncio.sleep(0.1)

        # Step 3: Send quantitative risk report
        quantitative_risk = analyzer.get_quantitative_risk(lookback_days=lookback_days)
        yield f"data: {json.dumps({'type': 'quantitative_risk', 'data': quantitative_risk})}\n\n"
        await asyncio.sleep(0.1)

        # Step 4: Send ESG report
        esg_risk = analyzer.get_esg_risk()
        yield f"data: {json.dumps({'type': 'esg_risk', 'data': esg_risk})}\n\n"
        await asyncio.sleep(0.1)

        # Step 5: Send anomaly detection report
        anomaly_risk = analyzer.get_anomaly_risk(lookback_days=lookback_days)
        yield f"data: {json.dumps({'type': 'anomaly_risk', 'data': anomaly_risk})}\n\n"
        await asyncio.sleep(0.1)

        # Step 6: Send overall risk report
        overall_risk = analyzer.calculate_overall_risk()
        yield f"data: {json.dumps({'type': 'overall_risk', 'data': overall_risk})}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    except ValueError as e:
        error_msg = str(e)
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"


@router.get("/risk-analysis/{ticker}/stream")
async def stream_risk_analysis(
        ticker: str,
        lookback_days: int = 30,
        db: Session = Depends(get_db)
):
    """
    Stream risk analysis data for a ticker incrementally using Server-Sent Events.

    This endpoint returns data in the following order:
    1. News articles
    2. News sentiment analysis
    3. Quantitative risk metrics
    4. ESG data
    5. Anomaly detection results
    6. Overall risk score and assessment

    Args:
        ticker: Stock ticker symbol
        lookback_days: Number of days to analyze (default: 30)

    Returns:
        Server-Sent Events stream with risk analysis data
    """
    return StreamingResponse(
        risk_analysis_stream(ticker, lookback_days, db),
        media_type="text/event-stream"
    )


@router.get("/risk-analysis/{ticker}")
async def get_risk_analysis(
        ticker: str,
        lookback_days: int = 30,
        db: Session = Depends(get_db)
):
    """
    Get complete risk analysis for a ticker in a single response.

    Args:
        ticker: Stock ticker symbol
        lookback_days: Number of days to analyze (default: 30)

    Returns:
        Complete risk analysis report
    """
    try:
        analyzer = RiskAnalysis(ticker=ticker, db=db)
        report = analyzer.generate_risk_report(lookback_days=lookback_days)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating risk report: {str(e)}"
        )
