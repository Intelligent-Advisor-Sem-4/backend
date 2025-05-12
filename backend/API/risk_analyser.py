from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
from typing import AsyncGenerator
from fastapi.encoders import jsonable_encoder

from db.dbConnect import get_db
from services.risk_analysis.analyser import RiskAnalysis

router = APIRouter(prefix="/risk-analysis", tags=["risk-analysis"])


async def risk_analysis_stream(ticker: str, lookback_days: int, db: Session) -> AsyncGenerator[str, None]:
    """Generate streaming risk analysis data with individual error handling for each section"""
    analyzer = RiskAnalysis(ticker=ticker, db=db)

    # Step 1: Send news articles
    try:
        news_articles = analyzer.get_news()
        serializable_articles = jsonable_encoder([article.dict() for article in news_articles])
        yield f"data: {json.dumps({'type': 'news_articles', 'data': serializable_articles})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'section_error', 'section': 'news_articles', 'message': str(e)})}\n\n"
    await asyncio.sleep(0.1)  # Small delay between messages

    # Step 2: News sentiment
    try:
        news_sentiment = analyzer.get_news_sentiment_risk(prefer_newest=False, use_llm=True)
        yield f"data: {json.dumps({'type': 'news_sentiment', 'data': jsonable_encoder(news_sentiment)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'section_error', 'section': 'news_sentiment', 'message': str(e)})}\n\n"
    await asyncio.sleep(0.1)

    # Step 3: Quantitative risk
    try:
        quantitative_risk = analyzer.get_quantitative_risk(lookback_days=lookback_days, use_llm=True)
        yield f"data: {json.dumps({'type': 'quantitative_risk', 'data': jsonable_encoder(quantitative_risk)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'section_error', 'section': 'quantitative_risk', 'message': str(e)})}\n\n"
    await asyncio.sleep(0.1)

    # Step 4: ESG risk
    try:
        esg_risk = analyzer.get_esg_risk()
        yield f"data: {json.dumps({'type': 'esg_risk', 'data': jsonable_encoder(esg_risk)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'section_error', 'section': 'esg_risk', 'message': str(e)})}\n\n"
    await asyncio.sleep(0.1)

    # Step 5: Anomaly risk
    try:
        anomaly_risk = analyzer.get_anomaly_risk(lookback_days=lookback_days)
        yield f"data: {json.dumps({'type': 'anomaly_risk', 'data': jsonable_encoder(anomaly_risk)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'section_error', 'section': 'anomaly_risk', 'message': str(e)})}\n\n"
    await asyncio.sleep(0.1)

    # Step 6: Overall risk
    try:
        overall_risk = analyzer.calculate_overall_risk()
        yield f"data: {json.dumps({'type': 'overall_risk', 'data': jsonable_encoder(overall_risk)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'section_error', 'section': 'overall_risk', 'message': str(e)})}\n\n"

    # Signal completion
    yield f"data: {json.dumps({'type': 'complete'})}\n\n"


@router.get("/{ticker}/stream")
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
        :param ticker:
        :param lookback_days:
        :param db:
    """
    return StreamingResponse(
        risk_analysis_stream(ticker, lookback_days, db),
        media_type="text/event-stream"
    )


@router.get("/{ticker}")
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


@router.get("/{ticker}/regenerate-news-analysis")
async def regenerate_news_analysis(
        ticker: str,
        db: Session = Depends(get_db)
):
    """
    Regenerate news analysis for a ticker.
    Args:
        ticker: Stock ticker symbol
        lookback_days: Number of days to analyze (default: 30)

    Returns:
        News analysis report
        :param ticker:
    """
    try:
        analyzer = RiskAnalysis(ticker=ticker, db=db)
        report = analyzer.get_news_sentiment_risk(prefer_newest=True, use_llm=True)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating news analysis report: {str(e)}"
        )
