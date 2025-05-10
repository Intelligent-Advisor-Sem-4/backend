import unittest
from unittest.mock import MagicMock
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


class TestTransactionCategorizerAgent(unittest.TestCase):
    def setUp(self):
        # Mock client with a chat completions interface
        self.mock_client = MagicMock()
        self.mock_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "description": "",
                            "amount": 0,
                            "type": "",
                            "category": ""
                        })
                    )
                )
            ]
        )

    def test_food_category(self):
        """Test that grocery transactions are categorized as Food"""
        # Configure mock response
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Whole Foods Market",
            "amount": 85.50,
            "type": "expense",
            "category": "Food"
        })
        
        result = transaction_categorizer_agent("Whole Foods Market", 85.50, "expense", self.mock_client)
        self.assertEqual(result["category"], "Food")

    def test_utilities_category(self):
        """Test that utility bills are categorized as Utilities"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Electricity Bill",
            "amount": 120.00,
            "type": "expense",
            "category": "Utilities"
        })
        
        result = transaction_categorizer_agent("Electricity Bill", 120.00, "expense", self.mock_client)
        self.assertEqual(result["category"], "Utilities")

    def test_income_category(self):
        """Test that salary payments are categorized as Work (income)"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Monthly Salary",
            "amount": 5000.00,
            "type": "income",
            "category": "Work"
        })
        
        result = transaction_categorizer_agent("Monthly Salary", 5000.00, "income", self.mock_client)
        self.assertEqual(result["category"], "Work")
        self.assertEqual(result["type"], "income")

    def test_entertainment_category(self):
        """Test that streaming services are categorized as Entertainment"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Netflix Subscription",
            "amount": 15.99,
            "type": "expense",
            "category": "Entertainment"
        })
        
        result = transaction_categorizer_agent("Netflix Subscription", 15.99, "expense", self.mock_client)
        self.assertEqual(result["category"], "Entertainment")

    def test_transportation_category(self):
        """Test that ride shares are categorized as Transportation"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Uber Ride",
            "amount": 25.75,
            "type": "expense",
            "category": "Transportation"
        })
        
        result = transaction_categorizer_agent("Uber Ride", 25.75, "expense", self.mock_client)
        self.assertEqual(result["category"], "Transportation")

    def test_invalid_json_response(self):
        """Test that the function handles invalid JSON responses gracefully"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = "invalid json"
        
        with self.assertRaises(json.JSONDecodeError):
            transaction_categorizer_agent("Test", 10.00, "expense", self.mock_client)

    def test_missing_category_field(self):
        """Test that the function handles responses missing the category field"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Test",
            "amount": 10.00,
            "type": "expense"
            # Missing category field
        })
        
        result = transaction_categorizer_agent("Test", 10.00, "expense", self.mock_client)
        self.assertNotIn("category", result)

    def test_case_insensitive_matching(self):
        """Test that the function handles case-insensitive descriptions"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "whole foods market",
            "amount": 85.50,
            "type": "expense",
            "category": "Food"
        })
        
        result = transaction_categorizer_agent("WHOLE FOODS MARKET", 85.50, "expense", self.mock_client)
        self.assertEqual(result["category"], "Food")

    def test_unrecognized_transaction(self):
        """Test that unrecognized transactions are categorized as Other"""
        self.mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "description": "Random Transaction",
            "amount": 10.00,
            "type": "expense",
            "category": "Other"
        })
        
        result = transaction_categorizer_agent("Random Transaction", 10.00, "expense", self.mock_client)
        self.assertEqual(result["category"], "Other")

if __name__ == "__main__":
    unittest.main()