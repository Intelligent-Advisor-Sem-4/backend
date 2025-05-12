import llm.transaction_categorization_agent as tc
import llm.financial_prediction_advisor_agent as fpa
import llm.budget_analysis_agent as ba
import llm.chat as chat
import openai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()  # Loads from .env file by default

# Initialize the client
client = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")  # Make sure your .env has this key
)

client1 = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")  # Make sure your .env has this key
)

client2 = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")  # Make sure your .env has this key
)

def getClient():
    return client

def getBudgetReport(transactions):
    return ba.budget_analyst_agent(transactions,clients=[client,client1,client2])

def getTransactionCategories(description,amount,transaction_type):
    return tc.transaction_categorizer_agent(description,amount,transaction_type,client=client)

def getFinancialAdvice(predictions,transactions):
    return fpa.prediction_advisor_agent(predictions,transactions,client=client)

def getChat(p):
    return chat.chat_with_llm(p,client=client)

# # Example usage
# connection = dc.create_connection()
# # Sample data
# transactions = dc.get_all_transactions(connection,1)  # List of past month's transactions
# new_transaction = ("Starbucks 123 Main St", 5.75, "expense")
# predictions = """Without Categories
#             Prediction for income:
#             Next day prediction: $498.340264871173
#             Next week prediction: $5676.0
#             Next month prediction: $24325.714285714286
#             ----------
#             Prediction for expense:
#             Next day prediction: $1591.5119331784035
#             Next week prediction: $12068.0
#             Next month prediction: $51720.0
#             ----------
#             Category based predictions
#             {'income': {'Business': 10.573714373162057, 'Government': 1.47, 'Work': 354.04156375085154, 'Investment': 22.50284719433377}, 'expense': {'Shopping': 25.38637587671553, 'Entertainment': 4.1723250342184915e-08, 'Education': 502.57202724357035, 'Personal': 0.1225, 'Health': 2.3990867734635707e-07, 'Food': 374.19029689614496, 'Transportation': 17.923119661756473}}
#             """  # Predicted budget data

# # Run agents
# # budget_report = ba.budget_analyst_agent(transactions[:5],client=client)
# # print("Budget Report:", budget_report)

# # category = tc.transaction_categorizer_agent(*new_transaction,client=client)
# # print("Transaction Category:", category)

# advice = fpa.prediction_advisor_agent(predictions,client=client)
# print("Financial Advice:", advice)