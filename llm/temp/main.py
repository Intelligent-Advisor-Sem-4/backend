import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import llm.temp.data_collector as data_collector
import llm.ml_model.manual_model as manual_model
import pandas as pd

def prediction(user_id=None, period='day'):
    output = []
    connection = data_collector.get_session()

    if connection:
        print("Connection successful!")
    else:
        print("Connection failed.")


    # Manual Model - Test1
    # print("Manual Model - Withput Categories")
    expense_data, income_data = data_collector.get_financial_dataframes_for_manual_model(connection)

    # Get today's date
    today = pd.to_datetime('today').normalize()  # Normalize to remove time component

    # Calculate today's values
    today_income = income_data[income_data['date'] == today]['total_spent'].sum()
    today_expense = expense_data[expense_data['date'] == today]['total_spent'].sum()

    # Calculate this week's values (assuming week starts on Monday)
    start_of_week = today - pd.to_timedelta(today.dayofweek, unit='d')
    this_week_income = income_data[income_data['date'] >= start_of_week]['total_spent'].sum()
    this_week_expense = expense_data[expense_data['date'] >= start_of_week]['total_spent'].sum()

    # Calculate this month's values
    start_of_month = today.replace(day=1)
    this_month_income = income_data[income_data['date'] >= start_of_month]['total_spent'].sum()
    this_month_expense = expense_data[expense_data['date'] >= start_of_month]['total_spent'].sum()

    # Handle cases where there might be no data (replace NaN with 0)
    today_income = 0 if pd.isna(today_income) else today_income
    today_expense = 0 if pd.isna(today_expense) else today_expense
    this_week_income = 0 if pd.isna(this_week_income) else this_week_income
    this_week_expense = 0 if pd.isna(this_week_expense) else this_week_expense
    this_month_income = 0 if pd.isna(this_month_income) else this_month_income
    this_month_expense = 0 if pd.isna(this_month_expense) else this_month_expense

    output.append(("today_income",today_income))
    output.append(("today_expense",today_expense))
    output.append(("this_week_income",this_week_income))
    output.append(("this_week_expense",this_week_expense))
    output.append(("this_month_income",this_month_income))
    output.append(("this_month_expense",this_month_expense))
    
    data_set = [income_data,expense_data]
    title = ['income', 'expense']
    for i in [0,1]:
        data = data_set[i]
        # Add day of week
        data['day_of_week'] = data['date'].dt.dayofweek + 1

        # Predictions
        next_day = manual_model.predict_next_day(data)
        next_week = manual_model.predict_next_week(data)
        next_month = manual_model.predict_next_month(data)

        # print(f"Prediction for {title_name}:")
        # print(f"Next day prediction: ${next_day.values[0]}")
        # print(f"Next week prediction: ${next_week}")
        # print(f"Next month prediction: ${next_month}")
        output.append((f"{title[i]}_next_day",next_day.values[0]))
        output.append((f"{title[i]}_next_week",next_week))
        output.append((f"{title[i]}_next_month",next_month))

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
        # Get data
    income_dfs = data_collector.get_daily_income_by_category(connection, user_id)
    expense_dfs = data_collector.get_daily_expenses_by_category(connection, user_id)
    
    income_preds = manual_model.predict_category_spending(income_dfs, period)
    expense_preds = manual_model.predict_category_spending(expense_dfs, period)
    
    # print("Category based predictions")
    # print(income_preds)
    # print(expense_preds)
    # output+="Category based predictions\nIncome:\n"+str(income_preds)+"\nExpense:\n"+str(expense_preds)+"\n"
    output.append(("income",income_preds))
    output.append(("expense",expense_preds))
    return dict(output)

def getTrascationOfMonth(user_id=None):
    connection = data_collector.get_session()
    return data_collector.get_all_transactions(connection,user_id=user_id)
     
if __name__ == "__main__":
    prediction()
    print(getTrascationOfMonth(1))