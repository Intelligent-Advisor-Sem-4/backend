from classes.RiskQuiz import RiskQuizAnswers

weights = {
    "age": 0.20,
    "investment_duration": 0.15,
    "investment_objective": 0.25,
    "financial_knowledge": 0.15,
    "market_reaction": 0.15,
    "income_stability": 0.10
}

score_mapping = {
    "age": {
        "Under 30": 100, "30-45": 80, "46-60": 50, "Above 60": 20
    },
    "investment_duration": {
        "Less than 2 years": 20, "2-5 years": 40, "6-10 years": 70, "More than 10 years": 100
    },
    "investment_objective": {
        "Capital Preservation": 20, "Income Generation": 40, 
        "Moderate Growth": 70, "Aggressive Growth": 100
    },
    "financial_knowledge": {
        "Limited": 20, "Average": 60, "Expert": 100
    },
    "market_reaction": {
        "Sell everything": 10, "Sell partially": 30, 
        "Hold and wait": 70, "Invest more": 100
    },
    "income_stability": {
        "Very unstable": 10, "Somewhat stable": 60, "Very stable": 100
    }
}

def calculate_weighted_score(answers: RiskQuizAnswers) -> float:
    total_score = (
        score_mapping["age"][answers.age] * weights["age"] +
        score_mapping["investment_duration"][answers.investment_duration] * weights["investment_duration"] +
        score_mapping["investment_objective"][answers.investment_objective] * weights["investment_objective"] +
        score_mapping["financial_knowledge"][answers.financial_knowledge] * weights["financial_knowledge"] +
        score_mapping["market_reaction"][answers.market_reaction] * weights["market_reaction"] +
        score_mapping["income_stability"][answers.income_stability] * weights["income_stability"]
    )
    return round(total_score, 2)

def personalized_profile(risk_percentage: float) -> str:
    if risk_percentage >= 80:
        return "Aggressive Investor"
    elif 60 <= risk_percentage < 80:
        return "Growth-oriented Investor"
    elif 40 <= risk_percentage < 60:
        return "Balanced Investor"
    elif 25 <= risk_percentage < 40:
        return "Conservative Investor"
    else:
        return "Risk-Averse Investor"


def calculate_personalized_risk(answers: RiskQuizAnswers):
    risk_percentage = calculate_weighted_score(answers)
    profile = personalized_profile(risk_percentage)
    return {
        "risk_percentage": risk_percentage,
        "personalized_profile": profile
    }