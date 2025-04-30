from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Literal


class KeyRisks(BaseModel):
    legal_risks: List[str] = Field(default_factory=list, description="Lawsuits, investigations, compliance failures")
    governance_risks: List[str] = Field(default_factory=list,
                                        description="Executive exits, board conflicts, control disputes")
    fraud_indicators: List[str] = Field(default_factory=list,
                                        description="Misstatements, shell entities, shady transactions")
    political_exposure: List[str] = Field(default_factory=list,
                                          description="Foreign influence, sanctions, subsidies, regulations")
    operational_risks: List[str] = Field(default_factory=list,
                                         description="Supply disruptions, recalls, safety breaches")
    financial_stability_issues: List[str] = Field(default_factory=list,
                                                  description="High leverage, poor liquidity, debt covenant stress")


class SentimentAnalysisResponse(BaseModel):
    stability_score: float = Field(
        ...,
        description="A score from -10 (extremely unstable/high risk) to +10 (extremely stable/secure)",
        ge=-10,
        le=10
    )
    stability_label: str = Field(
        ...,
        description="Risk level label",
        pattern="^(High Risk|Moderate Risk|Slight Risk|Stable|Very Stable)$"
    )
    key_risks: KeyRisks = Field(..., description="Key risk factors identified, categorized by type")
    security_assessment: str = Field(
        ...,
        description="Objective summary of potential threats to investor security and financial exposure",
    )
    customer_suitability: str = Field(
        ...,
        description="Suitability for customer inclusion based on investor protection concerns",
        pattern="^(Unsuitable|Cautious Inclusion|Suitable)$"
    )
    suggested_action: str = Field(
        ...,
        description="Recommended action based on risk assessment",
        pattern="^(Monitor|Flag for Review|Review|Flag for Removal|Immediate Action Required)$"
    )
    risk_rationale: List[str] = Field(
        ...,
        description="Concise bullet points justifying the score, label, and action using news-derived evidence",
    )
    news_highlights: Optional[List[str]] = Field(
        default_factory=list,
        description="Key headline-worthy excerpts that triggered concern or affected scoring"
    )
    risk_score: Optional[float] = Field(
        None,
        description="Derived risk score (0-10) based on stability score",
        ge=0,
        le=10
    )
    updated_at: Optional[str] = Field(
        None,
        description="Timestamp of the last update to the risk assessment",
    )
    error_details: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "stability_score": 2.5,
                "stability_label": "Moderate Risk",
                "key_risks": {
                    "legal_risks": ["Ongoing regulatory investigation in EU markets"],
                    "governance_risks": ["Recent CFO departure"],
                    "fraud_indicators": [],
                    "political_exposure": ["Increasing tariff pressures in key markets"],
                    "operational_risks": ["Supply chain disruptions reported in Q2"],
                    "financial_stability_issues": ["Debt covenant approaching threshold"]
                },
                "security_assessment": "The company faces moderate regulatory and operational challenges that could impact short-term financial performance. While core business remains stable, investors should monitor developments in EU regulatory actions and supply chain recovery timelines.",
                "customer_suitability": "Cautious Inclusion",
                "suggested_action": "Flag for Review",
                "risk_rationale": [
                    "Multiple regulatory investigations create uncertainty around potential fines or restrictions.",
                    "Recent executive departures and supply disruptions suggest operational instability."
                ],
                "news_highlights": [
                    "CFO departure announced amid quarterly earnings miss",
                    "EU regulators launching formal investigation into market practices"
                ],
                "risk_score": 7.5,
                "updated_at": "2023-10-01T12:00:00Z",
            }
        }


class QuantRiskMetrics(BaseModel):
    volatility_score: Optional[float] = None
    beta_score: Optional[float] = None
    rsi_risk: Optional[float] = None
    volume_risk: Optional[float] = None
    debt_risk: Optional[float] = None
    eps_risk: Optional[float] = None
    quant_risk_score: Optional[float] = None


class QuantRiskResponse(BaseModel):
    volatility: Optional[float] = None
    beta: Optional[float] = None
    rsi: Optional[float] = None
    volume_change_percent: Optional[float] = None
    debt_to_equity: Optional[float] = None
    risk_metrics: QuantRiskMetrics
    risk_label: Optional[str] = None  # This is StabilityLabel in original
    risk_explanation: Optional[str] = None
    error_details: Optional[str] = None
    error: Optional[str] = None


class EsgRiskResponse(BaseModel):
    total_esg: Optional[float] = None
    environmental_score: Optional[float] = None
    social_score: Optional[float] = None
    governance_score: Optional[float] = None
    esg_risk_score: Optional[float] = None


class AnomalyFlag(BaseModel):
    type: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[float] = None


class AnomalyDetectionResponse(BaseModel):
    flags: Optional[List[AnomalyFlag]] = None
    anomaly_score: Optional[float] = Field(None, description="Range: 0 to 10")


class NewsArticle(BaseModel):
    # Note: The NewsArticle structure wasn't included in your provided interfaces
    # I'm creating a placeholder - you'll need to update this with the actual fields
    title: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None
    source: Optional[str] = None
    content: Optional[str] = None


class RiskComponent(BaseModel):
    weight: Optional[float] = None
    score: Optional[float] = Field(None, description="Range: 0 to 10")


class OverallRiskComponents(BaseModel):
    news_sentiment: Optional[RiskComponent] = None
    quant_risk: Optional[RiskComponent] = None
    esg_risk: Optional[RiskComponent] = None
    anomaly_detection: Optional[RiskComponent] = None


class OverallRiskResponse(BaseModel):
    overall_risk_score: Optional[float] = Field(None, description="Range: 0 to 10")
    risk_level: Optional[Literal["Low", "Medium", "High"]] = None
    components: Optional[OverallRiskComponents] = None


class StreamResponse(BaseModel):
    type: Literal["news_articles", "news_sentiment", "quantitative_risk",
    "esg_risk", "anomaly_risk", "overall_risk", "complete"]
    data: Optional[Union[OverallRiskResponse, NewsArticle, SentimentAnalysisResponse,
    QuantRiskResponse, EsgRiskResponse, AnomalyDetectionResponse]] = None
