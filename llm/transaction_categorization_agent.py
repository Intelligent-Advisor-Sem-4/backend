import json

# Categories
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


def transaction_categorizer_agent(description, amount, transaction_type, client):
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


def generate_transaction_prompt(description, amount, transaction_type):
    """Generates an AI prompt for transaction categorization with enhanced context awareness."""
    prompt = f"""
    Categorize this {transaction_type} transaction with high accuracy:
    Description: {description}
    Amount: {amount}

    Use ONLY these categories:
    {budget_categories}

    Guidelines for categorization:
    1. Pay special attention to brand names and merchants (e.g., "Whiskers" = pet food, "Uber" = transportation)
    2. Consider the transaction amount for context (large amounts for "Property" vs small for "Food")
    3. Look for keywords that indicate the purpose (e.g., "premium", "subscription", "bill", "salary")
    4. If a transaction could fit multiple categories, choose the most specific one
    5. For recurring services, categorize based on the primary purpose, not the payment method

    Common patterns to recognize:
    - Grocery stores/supermarkets → Food
    - Monthly bills with company names → Utilities
    - Streaming services → Entertainment
    - Online retailers → Shopping
    - Medical facilities/pharmacies → Health
    - Investment platforms → Investments
    - Educational institutions → Education
    - Gas stations/rideshares → Transportation
    - Government agencies → Government
    - Loan payments → Debt Payments
    - SaaS/digital subscriptions → Technology or Services
    - Pet supplies/veterinary → Pets
    - Restaurants/food delivery → Food or Entertainment
    - Salons/spas → Personal Care

    Respond in JSON format:
    {{
        "description": "original description",
        "amount": original_amount,
        "type": "income/expense",
        "category": "determined_category",
        "confidence": "high/medium/low"  // Added confidence level
    }}
    """
    return prompt
