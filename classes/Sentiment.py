from pydantic import BaseModel, Field, conlist, conint, constr
from typing import List, Dict, Optional, Union, Any


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
    error_details: Optional[str] = None

    class Config:
        schema_extra = {
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
                "risk_score": 7.5
            }
        }
