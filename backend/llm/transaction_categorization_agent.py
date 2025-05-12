import json

#Categories
budget_categories = [
    # Essential Expenses
    "Property",
    "Utilities",
    "Food",
    "Transportation",
    "Health",
    "Debt Payments",
    "Insurance",
    "Work",
    
    # Lifestyle Expenses
    "Entertainment",
    "Shopping",
    "Travel",
    "Personal Care",
    "Education",
    "Personal",
    
    # Savings & Investments
    "Emergency Fund",
    "Retirement",
    "Investments",
    "Big Purchases",
    "Savings",
    "Bussiness",
    
    # Miscellaneous
    "Charity",
    "Pets",
    "Childcare",
    "Government",
    "Technology",
    "Services",
    "Other"
]

def transaction_categorizer_agent(description, amount, transaction_type,client):
    """Categorizes transactions based on description"""
    prompt = f"""
    Categorize this {transaction_type} transaction:
    Description: {description}
    Amount: {amount}

    Use ONLY these categories:
    {budget_categories}

    Respond in JSON format:
    {{
        "description": "original description",
        "amount": original_amount,
        "type": "income/expense",
        "category": "determined_category",
    }}
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)