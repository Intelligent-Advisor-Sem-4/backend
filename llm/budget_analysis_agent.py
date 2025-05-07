from collections import defaultdict
import time

def calculate_financial_summary(transaction_history):
    """Manually calculates financial metrics from transaction history"""
    total_income = 0.0
    total_expenses = 0.0
    category_spending = defaultdict(float)
    
    for transaction in transaction_history:
        amount = transaction['amount']  # Assuming amount is the last element
        if transaction['type'].lower() == 'income':  # Assuming type is at index 3
            total_income += amount
        else:
            total_expenses += amount
            category = transaction['category']  # Assuming category is at index 5
            category_spending[category] += amount
    
    net_savings = total_income - total_expenses
    
    # Calculate top spending categories
    total_spending = sum(category_spending.values())
    top_categories = []
    if total_spending > 0:
        top_categories = sorted(
            [(cat, (amt/total_spending)*100) for cat, amt in category_spending.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]  # Get top 3 categories
    
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_savings": net_savings,
        "top_spending_categories": top_categories
    }

# def assesment_agent(transaction_history,client):
#     prompt = f"""
#     Analyze this transaction history for the past month and provide an Assessment of spending health (Good/Moderate/Poor)

#     Transaction History: [(date, type, reason, category, amount )]
#     {transaction_history}

#     Just give me a text response
#     """
    
#     completion = client.chat.completions.create(
#         model="writer/palmyra-fin-70b-32k",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.1,  # Lower for more factual analysis
#         response_format={"type": "json_object"}
#     )
#     return completion.choices[0].message.content

def recommendations_agent(transaction_history,client):
    prompt = f"""
    Analyze this transaction history for the past month and provide specific optimization recommendations and Any urgent alerts

    Transaction History: [(date, type, reason, category, amount )]
    {transaction_history}

    Just give me a text response in this format
    recomendation1,recomendation2,recomendation3,...|alert1,alert2,alert3,...
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Lower for more factual analysis
        response_format={"type": "json_object"}
    )

    recomendations, alerts = completion.choices[0].message.content.replace("\n","").replace("\\","").replace("\n","").replace("\"","").split("|") 
    return recomendations.split(","),alerts.split(",")

# def alert_agent(transaction_history,client):
#     prompt = f"""
#     Analyze this transaction history for the past month and provide Any urgent alerts

#     Transaction History: [(date, type, reason, category, amount )]
#     {transaction_history}

#     Just give me a text response seperated by commas
#     """
    
#     completion = client.chat.completions.create(
#         model="writer/palmyra-fin-70b-32k",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.1,  # Lower for more factual analysis
#         response_format={"type": "json_object"}
#     )
#     return completion.choices[0].message.content.replace("\n","").replace("\\","").replace("\n","").replace("\"","").split(",")

def budget_analyst_agent(transaction_history,clients):
    """Analyzes past month's spending patterns and gives recommendations"""
    data = []
    for txn in transaction_history:
        data.append((txn['date'],txn['type'],txn['reason'],txn['category'],txn['amount']))

    r,a = recommendations_agent(data,clients[1])
    return {
        "summary": calculate_financial_summary(transaction_history),
        "assessment": "",
        "recommendations": r,
        "alerts": a
    }

# import json


# def get_spending_assessment(client, summary):
#     """Gets spending health assessment from LLM"""
#     prompt = f"""
#     Based on these financial metrics, provide a spending health assessment (Good/Moderate/Poor) 
#     with a brief explanation. Consider typical budgeting guidelines.
    
#     Financial Summary:
#     - Monthly Income: ${summary['total_income']:,.2f}
#     - Monthly Expenses: ${summary['total_expenses']:,.2f}
#     - Net Savings: ${summary['net_savings']:,.2f}
#     - Top Spending Categories: {summary['top_spending_categories']}
    
#     Respond in this JSON format:
#     {{
#         "assessment": "text",
#         "explanation": "text"
#     }}
#     """
    
#     completion = client.chat.completions.create(
#         model="writer/palmyra-fin-70b-32k",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.1,
#         response_format={"type": "json_object"}
#     )
#     res = json.loads(completion.choices[0].message.content)
#     print(res)
#     return json.loads(res)

# def get_spending_recommendations(client, summary, assessment):
#     """Gets personalized spending recommendations from LLM"""
#     prompt = f"""
#     Based on this financial summary and assessment, provide three specific 
#     and actionable optimization recommendations for better budgeting.
    
#     Financial Summary:
#     - Monthly Income: ${summary['total_income']:,.2f}
#     - Monthly Expenses: ${summary['total_expenses']:,.2f}
#     - Net Savings: ${summary['net_savings']:,.2f}
#     - Top Spending Categories: {summary['top_spending_categories']}
    
#     Respond in this JSON format:
#     {{
#         "recommendations": ["text", "text", "text"]
#     }}
#     """
    
#     completion = client.chat.completions.create(
#         model="writer/palmyra-fin-70b-32k",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.1,
#         response_format={"type": "json_object"}
#     )
#     print(completion.choices[0].message.content)
#     return json.loads(completion.choices[0].message.content)

# def check_for_alerts(summary):
#     """Manually checks for urgent financial alerts"""
#     alerts = []
    
#     # Check for negative net savings
#     if summary['net_savings'] < 0:
#         alerts.append("Alert: You're spending more than you earn this month!")
    
#     # Check if savings rate is very low (less than 10% of income)
#     if summary['total_income'] > 0 and (summary['net_savings'] / summary['total_income']) < 0.1:
#         alerts.append("Notice: Your savings rate is below recommended 10% of income")
    
#     # Check for unusually high spending in any category (>50% of income)
#     for category, percent in summary['top_spending_categories']:
#         if percent > 50:
#             alerts.append(f"Warning: High spending in {category} ({percent:.1f}% of total expenses)")
    
#     return alerts

# def budget_analyst_agent(transaction_history, client):
#     """Analyzes past month's spending through separate steps"""
#     # 1. Manual calculations
#     summary = calculate_financial_summary(transaction_history)
    
#     # 2. Get assessment from LLM
#     assessment = get_spending_assessment(client, summary)
    
#     # 3. Get recommendations from LLM
#     recommendations = get_spending_recommendations(client, summary, assessment)
    
#     # 4. Manual alert checks
#     alerts = check_for_alerts(summary)
    
#     # Combine all results
#     result = {
#         "summary": summary,
#         "assessment": assessment['assessment'],
#         "assessment_explanation": assessment['explanation'],
#         "recommendations": recommendations['recommendations'],
#         "alerts": alerts
#     }
    
#     return result