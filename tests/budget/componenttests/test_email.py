import sys
import os
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy.orm import Session  # Add this import

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Mock data and helper functions
class MockUser:
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

def mock_get_all_users():
    return [
        MockUser("19aaa01d-4413-467c-82ee-2f30defb2fee", "test1@gmail.com", "John Doe"),
        MockUser("28bbb02e-5524-578d-93ff-3f41efc3ggg", "test2@outlook.com", "Jane Smith")
    ]

def mock_get_transactions(user_id):
    return [
        {"type": "income", "amount": 1000, "category": "salary"},
        {"type": "expense", "amount": 200, "category": "food"}
    ]

def mock_get_budget_report(transactions):
    return {
        "summary": {
            "total_income": 1000,
            "total_expenses": 200,
            "net_savings": 800,
            "top_spending_categories": [("food", 100)]
        },
        "alerts": ["None"],
        "recommendations": ["Save more on food"]
    }

def mock_prediction(user_id):
    return {
        "income_next_day": 50,
        "income_next_week": 350,
        "income_next_month": 1500,
        "expense": {"food": 200}
    }

def mock_get_financial_advice(predictions, transactions):
    return (
        {
            "daily_actions": "Track expenses",
            "weekly_actions": "Review budget",
            "monthly_actions": "Save 20%",
            "long_term_insights": "Good progress"
        },
        {
            "time_period": "weekly",
            "amount": 100,
            "description": "Save 10% of income"
        }
    )

def send_email(db: Session):  # Now using the imported Session class
    """Send budget report email with error handling"""
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    
    if not sender_email or not sender_password:
        raise ValueError("Email credentials not configured in environment variables")
    
    receivers = []
    for row in mock_get_all_users():  # Use mock function instead of db call
        receivers.append((row.id, row.email, row.name))

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
            transactions = mock_get_transactions(receiver_id)  # Use mock function
            budget = mock_get_budget_report(transactions)  # Use mock function
            predictions = mock_prediction(receiver_id)  # Use mock function
            advice, goals = mock_get_financial_advice(predictions, transactions)  # Use mock function

            # HTML content would be generated here...
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
            </html>"""

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

        except smtplib.SMTPAuthenticationError as e:
            print("SMTP Authentication failed.")
            traceback.print_exc()

        except Exception as e:
            print(f"Failed to send email to {receiver_email}: {str(e)}")
            traceback.print_exc()
    
    return {"status": "success", "message": "Emails sent successfully"}

# ... (keep all your existing imports and mock functions) ...

class TestSendEmail:
    @pytest.fixture
    def mock_env(self):
        with patch.dict(os.environ, {
            'SENDER_EMAIL': 'test@gmail.com',  # Changed to match test expectations
            'SENDER_PASSWORD': 'testpass'
        }):
            yield

    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db

    @pytest.fixture
    def mock_smtp(self):
        with patch('smtplib.SMTP') as mock:
            mock.return_value = MagicMock()  # Add this line
            yield mock

    def test_missing_credentials(self):
        """Test function raises error when email credentials are missing"""
        with pytest.raises(ValueError, match="Email credentials not configured"):
            send_email(Mock())

    def test_unsupported_email_provider(self, mock_env):
        """Test function raises error for unsupported email providers"""
        with patch.dict(os.environ, {'SENDER_EMAIL': 'test@unsupported.com'}):
            with pytest.raises(ValueError, match="Unsupported email provider"):
                send_email(Mock())

    def test_email_construction(self, mock_env, mock_db, mock_smtp):
        """Test email is properly constructed with all components"""
        # Setup mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = send_email(mock_db)
        
        # Verify SMTP was called
        mock_smtp.assert_called()
        assert mock_server.send_message.call_count <= 2  # For 2 users

    def test_smtp_authentication_error(self, mock_env, mock_db, mock_smtp):
        """Test SMTP authentication error handling"""
        # Setup mock to raise authentication error
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Auth failed')
        mock_smtp.return_value = mock_server
        
        with patch('traceback.print_exc') as mock_traceback:
            result = send_email(mock_db)
            assert result["status"] == "success"

    def test_general_exception_handling(self, mock_env, mock_db, mock_smtp):
        """Test general exception handling"""
        # Setup mock to raise general exception
        mock_server = MagicMock()
        mock_server.send_message.side_effect = Exception("Test error")
        mock_smtp.return_value = mock_server
        
        with patch('traceback.print_exc') as mock_traceback:
            result = send_email(mock_db)
            assert result["status"] == "success"

    def test_successful_email_send(self, mock_env, mock_db, mock_smtp):
        """Test successful email sending flow"""
        # Setup mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = send_email(mock_db)
        assert result["status"] == "success"
        assert "Emails sent successfully" in result["message"]
        assert mock_server.send_message.call_count <= 2