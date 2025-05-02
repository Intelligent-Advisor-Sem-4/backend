import json
def budget_analyst_agent(transaction_history,client):
    """Analyzes past month's spending patterns and gives recommendations"""
    prompt = f"""
    Analyze this transaction history for the past month and provide:
    1. A spending summary (total income, expenses, net savings)
    2. Assessment of spending health (Good/Moderate/Poor)
    3. Three specific optimization recommendations
    4. Any urgent alerts

    Transaction History: [(id, user name, date, type, reason, category, amount )]
    {transaction_history}

    Respond in this JSON format:
    {{
        "summary": {{
            "total_income": float,
            "total_expenses": float,
            "net_savings": float,
            "top_spending_categories": [("category", percentage),...]
        }},
        "assessment": "text",
        "recommendations": ["text",...],
        "alerts": ["text",...]
    }}
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Lower for more factual analysis
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)