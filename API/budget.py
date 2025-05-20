from enum import Enum
import json
from fastapi import Depends, APIRouter
import sys
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import json
import traceback
from dotenv import load_dotenv

from llm.transaction_categorization_agent import generate_transaction_prompt
from services.llm.llm import generate_content_with_llm, LLMProvider, GeminiModel
from services.utils import parse_llm_json_response

load_dotenv()

from db.dbConnect import get_db

sys.path.append(str(Path(__file__).parent.parent))
from llm.temp.main import prediction, getTrascationOfMonth
import llm.sub_llm as sub_llm
from typing import List
from sqlalchemy.orm import Session
# from models.models import Transaction, BudgetGoal
from services.budget_service.schemas import (
    TransactionCreate,
    TransactionUpdate,
    BudgetGoalCreate,
    BudgetGoalUpdate,
    TransactionSummary,
    Transaction,
    BudgetGoal
)
from services.budget_service.budget_services import (
    get_transactions_by_user,
    create_transaction,
    getAllUsers,
    update_transaction,
    delete_transaction,
    get_transactions_by_category,
    get_transaction_summary,
    get_budget_goals,
    create_budget_goal,
    update_budget_goal,
    delete_budget_goal
)

router = APIRouter(prefix='/budget')


@router.get("/predictions")
async def get_predictions(user_id: str):
    """Endpoint 1: Get financial predictions and advice"""
    predictions = prediction(user_id)
    transactions = getTrascationOfMonth(user_id)
    # print(predictions)
    if len(transactions) == 0:
        predictions['uid'] = user_id
        return {
            "predictions": predictions,
            "financial_advice": {
                "observations": "",
                "daily_actions": "",
                "weekly_actions": "",
                "monthly_actions": "",
                "risks": "",
                "long_term_insights": ""
            },
            "budget_goals": []
        }
    advice, goals = sub_llm.getFinancialAdvice(predictions, transactions)
    predictions['uid'] = user_id
    print(advice)
    print(goals)
    return {
        "predictions": predictions,
        "financial_advice": advice,
        "budget_goals": [goals]
    }


@router.get("/budget-report")
async def get_budget_report(user_id: str):
    """Endpoint 2: Get budget report for a specific month"""
    transactions = getTrascationOfMonth(user_id)
    print(transactions)
    budget = sub_llm.getBudgetReport(transactions)
    # print(transactions)
    print(budget)
    return {
        "transactions": transactions,
        "budget_report": budget
    }


@router.get("/categorize-transaction")
async def categorize_transaction(description: str, amount: float, type: str):
    """Endpoint 3: Categorize a new transaction"""
    # res = sub_llm.getTransactionCategories(description, amount, type)

    prompt = generate_transaction_prompt(description, amount, type)
    geminiResponse = generate_content_with_llm(prompt=prompt, llm_provider=LLMProvider.GEMINI,
                                               gemini_model=GeminiModel.FLASH_LITE)
    res = parse_llm_json_response(geminiResponse)

    print(res)
    return res


@router.get("/chat")
async def chat(prompt: str):
    """Endpoint 4: Chat with the LLM"""
    print(prompt)
    response = sub_llm.getChat(prompt)
    print(response)
    return {
        "response": response
    }


@router.get("/email")
async def send_email(db: Session = Depends(get_db)):
    """Send budget report email with error handling"""
    sender_email = os.environ.get('GMAIL_USER')
    sender_password = os.environ.get('GMAIL_PASSWORD')

    if not sender_email or not sender_password:
        raise ValueError("Email credentials not configured in environment variables")

    # receivers = [("19aaa01d-4413-467c-82ee-2f30defb2fee", 'smudunlahiru@gmail.com', "John Doe")]
    receivers = []
    for row in getAllUsers(db):
        receivers.append((row.id, (row.email if "gmail" in row.email else "smudunlahiru@gmail.com"), row.name))

    print(receivers)

    subject = f"Your Budget Report - {datetime.now().strftime('%Y-%m-%d')}"
    smtp_config = {
        'gmail.com': ('smtp.gmail.com', 587),
        'outlook.com': ('smtp.office365.com', 587),
        'hotmail.com': ('smtp.office365.com', 587),
        'yahoo.com': ('smtp.mail.yahoo.com', 587)
    }

    domain = sender_email.split('@')[-1]
    smtp_server, smtp_port = smtp_config.get(domain, (None, None))

    if not smtp_server:
        raise ValueError(f"Unsupported email provider: {domain}")

    for receiver_id, receiver_email, receiver_name in receivers:
        try:
            transactions = getTrascationOfMonth(receiver_id)
            budget = sub_llm.getBudgetReport(transactions)
            predictions = prediction(receiver_id)
            advice, goals = sub_llm.getFinancialAdvice(predictions, transactions)

            # Beautified HTML content
            html = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: 'Arial', sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 800px;
                            margin: 0 auto;
                            padding: 20px;
                            background-color: #f9f9f9;
                        }}
                        .header {{
                            color: #2E86C1;
                            border-bottom: 2px solid #e0e0e0;
                            padding-bottom: 10px;
                            margin-bottom: 30px;
                            text-align: center;
                        }}
                        .card {{
                            background: white;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                            padding: 20px;
                            margin-bottom: 25px;
                        }}
                        .card-title {{
                            color: #117A65;
                            margin-top: 0;
                            margin-bottom: 15px;
                            font-size: 18px;
                        }}
                        .summary-grid {{
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 15px;
                            margin-bottom: 20px;
                        }}
                        .summary-item {{
                            background: #f5f9ff;
                            padding: 12px;
                            border-radius: 6px;
                            text-align: center;
                        }}
                        .summary-value {{
                            font-size: 20px;
                            font-weight: bold;
                            color: #2E86C1;
                            margin: 5px 0;
                        }}
                        .summary-label {{
                            font-size: 13px;
                            color: #666;
                        }}
                        .category-list {{
                            margin-top: 15px;
                        }}
                        .category-item {{
                            display: flex;
                            justify-content: space-between;
                            padding: 8px 0;
                            border-bottom: 1px solid #eee;
                        }}
                        .category-name {{
                            font-weight: 500;
                        }}
                        .category-value {{
                            color: #117A65;
                            font-weight: bold;
                        }}
                        .recommendation-item {{
                            padding: 8px 0;
                            border-bottom: 1px dashed #eee;
                            display: flex;
                            align-items: flex-start;
                        }}
                        .recommendation-item:before {{
                            content: "•";
                            color: #2E86C1;
                            margin-right: 10px;
                            font-size: 20px;
                        }}
                        .goal-card {{
                            background: #f0f7f4;
                            padding: 15px;
                            border-radius: 6px;
                            margin-top: 10px;
                        }}
                        .goal-period {{
                            display: inline-block;
                            background: #117A65;
                            color: white;
                            padding: 3px 8px;
                            border-radius: 4px;
                            font-size: 12px;
                            margin-right: 10px;
                        }}
                        .footer {{
                            margin-top: 40px;
                            padding-top: 15px;
                            border-top: 1px solid #e0e0e0;
                            color: #777;
                            text-align: center;
                            font-size: 14px;
                        }}
                        .alert-badge {{
                            background: #fff8e6;
                            border-left: 3px solid #ffc107;
                            padding: 10px;
                            margin-top: 15px;
                            font-size: 14px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>Hello, {receiver_name}</h2>
                        <p>Your personalized financial report</p>
                    </div>

                    <!-- Budget Summary Card -->
                    <div class="card">
                        <h3 class="card-title">Budget Summary</h3>
                        
                        <div class="summary-grid">
                            <div class="summary-item">
                                <div class="summary-label">Total Income</div>
                                <div class="summary-value">${budget['summary']['total_income']:.2f}</div>
                            </div>
                            <div class="summary-item">
                                <div class="summary-label">Total Expenses</div>
                                <div class="summary-value">${budget['summary']['total_expenses']:.2f}</div>
                            </div>
                            <div class="summary-item">
                                <div class="summary-label">Net Savings</div>
                                <div class="summary-value">${budget['summary']['net_savings']:.2f}</div>
                            </div>
                        </div>
                        
                        <h4>Top Spending Categories</h4>
                        <div class="category-list">
                            {''.join(f'<div class="category-item"><span class="category-name">{category[0]}</span><span class="category-value">{category[1]:.1f}%</span></div>'
                                     for category in budget['summary']['top_spending_categories'])}
                        </div>
                        
                        {f'<div class="alert-badge">⚠️ {budget["alerts"][0].strip()}</div>'
            if budget['alerts'][0].strip() != "None" else ''}
                    </div>

                    <!-- Financial Predictions Card -->
                    <div class="card">
                        <h3 class="card-title">Financial Predictions</h3>
                        
                        <h4>Next Period Forecast</h4>
                        <div class="summary-grid">
                            <div class="summary-item">
                                <div class="summary-label">Next Day Income</div>
                                <div class="summary-value">${predictions['income_next_day']:.2f}</div>
                            </div>
                            <div class="summary-item">
                                <div class="summary-label">Next Week Income</div>
                                <div class="summary-value">${predictions['income_next_week']:.2f}</div>
                            </div>
                            <div class="summary-item">
                                <div class="summary-label">Next Month Income</div>
                                <div class="summary-value">${predictions['income_next_month']:.2f}</div>
                            </div>
                        </div>
                        
                        <h4>Expense Breakdown</h4>
                        <div class="category-list">
                            {''.join(f'<div class="category-item"><span class="category-name">{category}</span><span class="category-value">${amount:.2f}</span></div>'
                                     for category, amount in predictions['expense'].items())}
                        </div>
                    </div>

                    <!-- Recommendations Card -->
                    <div class="card">
                        <h3 class="card-title">Recommendations</h3>
                        
                        <div class="category-list">
                            {''.join(f'<div class="recommendation-item">{recommendation}</div>'
                                     for recommendation in budget['recommendations'])}
                        </div>
                        
                        <h4>Action Plan</h4>
                        <div class="goal-card">
                            <p><strong>Daily:</strong> {advice['daily_actions']}</p>
                            <p><strong>Weekly:</strong> {advice['weekly_actions']}</p>
                            <p><strong>Monthly:</strong> {advice['monthly_actions']}</p>
                        </div>
                    </div>

                    <!-- Goals Card -->
                    <div class="card">
                        <h3 class="card-title">Financial Goals</h3>
                        
                        <div class="goal-card">
                            <span class="goal-period">{goals['time_period']}</span>
                            <strong>${goals['amount']:.2f}</strong>
                            <p>{goals['description']}</p>
                        </div>
                        
                        <p style="margin-top: 15px; font-style: italic;">{advice['long_term_insights']}</p>
                    </div>

                    <div class="footer">
                        <p>Best regards,</p>
                        <p><strong>Your Budget Team</strong></p>
                    </div>
                </body>
            </html>
            """

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            print(f"Email successfully sent to {receiver_email}")
            # return {"status": "success", "message": f"Email sent to {receiver_email}"}

        except smtplib.SMTPAuthenticationError as e:
            print("SMTP Authentication failed.")
            print("Check the following:")
            print("1. Are you using an App Password instead of your main password?")
            print("2. Is 2FA enabled on your email account?")
            print("3. Is SMTP access allowed for your provider?")
            traceback.print_exc()
            # return {"status": "fail", "error": "Authentication failed"}

        except Exception as e:
            print(f"Failed to send email to {receiver_email}: {str(e)}")
            traceback.print_exc()
            # return {"status": "fail", "error": str(e)}
    return {"status": "success", "message": "Emails sent successfully"}


@router.get("/transactions/{user_id}", response_model=List[Transaction])
async def get_expenses_by_user_id(user_id: str, db: Session = Depends(get_db)):
    return get_transactions_by_user(db, user_id)


@router.post("/transactions", response_model=Transaction)
async def create_expense(expense: TransactionCreate, db: Session = Depends(get_db)):
    print(expense)
    return create_transaction(db, expense)


@router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_expense(
        transaction_id: int,
        updates: TransactionUpdate,
        db: Session = Depends(get_db)
):
    return update_transaction(db, transaction_id, updates)


@router.delete("/transactions/{transaction_id}")
async def delete_expense(transaction_id: int, db: Session = Depends(get_db)):
    return delete_transaction(db, transaction_id)


@router.get("/transactions/categories/{user_id}")
async def get_expenses_by_category(user_id: str, db: Session = Depends(get_db)):
    return get_transactions_by_category(db, user_id)


@router.get("/transactions/summary/{user_id}", response_model=TransactionSummary)
async def get_summary_by_user_id(user_id: str, db: Session = Depends(get_db)):
    return get_transaction_summary(db, user_id)


@router.get("/budget-goals/{user_id}", response_model=List[BudgetGoal])
async def get_budget_goals_endpoint(user_id: str, db: Session = Depends(get_db)):
    return get_budget_goals(db, user_id)


@router.post("/budget-goals", response_model=BudgetGoal)
async def create_budget_goal_endpoint(goal: BudgetGoalCreate, db: Session = Depends(get_db)):
    return create_budget_goal(db, goal)


@router.put("/budget-goals/{goal_id}", response_model=BudgetGoal)
async def update_budget_goal_endpoint(
        goal_id: int,
        updates: BudgetGoalUpdate,
        db: Session = Depends(get_db)
):
    return update_budget_goal(db, goal_id, updates)


@router.delete("/budget-goals/{goal_id}")
async def delete_budget_goal_endpoint(goal_id: int, db: Session = Depends(get_db)):
    return delete_budget_goal(db, goal_id)
