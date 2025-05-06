from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from db.dbConnect import get_db,engine

# Load environment variables
load_dotenv()

def create_db_engine():
    """Create and return a SQLAlchemy engine using explicit connection parameters"""
    # Build connection URL from components
    db_config = {
        'username': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        'database': os.getenv('DB_NAME')
    }

    # Construct the connection URL
    db_url = (
        f"postgresql+psycopg2://{db_config['username']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )

    # Connection pool settings
    engine_params = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_pre_ping': True,
        'pool_recycle': 300,  # Recycle connections after 5 minutes
        'connect_args': {
            'connect_timeout': 5,  # 5 second connection timeout
            'options': '-c statement_timeout=30000'  # 30 second statement timeout
        }
    }

    return create_engine(db_url, **engine_params)

# # Create engine and session factory
# engine = create_db_engine()
# Session = sessionmaker(bind=engine)

def get_session():
    """Create and return a database session"""
    # engine = get_db()
    # Session = sessionmaker(bind=engine) 
    return get_db()

def execute_query(session, query, params=None, fetch=False):
    """Execute a SQL query and optionally return results"""
    try:
        if isinstance(query, str):
            query = text(query)
        with engine.connect() as connection:
            result = connection.execute(query, params)
            print("Database connection successful!")
            # print(result.fetchall())
        # result = session.execute(query, params or {})
        # if fetch:
        #     return result.fetchall()
        # session.commit()
        return result.fetchall() if fetch else None
    except Exception as e:
        print(f"Error executing query: {e}")
        # session.rollback()
        raise  # Re-raise the exception after rollback
    finally:
        # session.close()
        connection.close()

def get_all_transactions(session, days=30, user_id=None):
    """Get all transactions from the last N days (optionally for specific user)"""
    query = """
    SELECT 
        t.id, 
        u.name, 
        t.created_at, 
        t.type,
        t.reason, 
        t.category, 
        t.amount
    FROM transactions t
    JOIN "users" u ON t.user_id = u.id
    WHERE t.created_at >= :start_date
    {user_condition}
    ORDER BY t.created_at DESC
    """
    
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d') if days > 0 else '1970-01-01'
    params = {'start_date': start_date}
    
    if user_id:
        query = query.format(user_condition="AND t.user_id = :user_id")
        params['user_id'] = user_id
    else:
        query = query.format(user_condition="")
    
    res = execute_query(session, query, params, fetch=True)
    return [{"id":int(id),"user_name":str(user_name),"date":str(date),"type":str(type),"reason":str(reason),"category":str(category), "amount":float(amount)} for id,user_name,date,type,reason,category, amount in res] if res else []

def get_daily_expenses(session, user_id=None, start_date=None, end_date=None):
    """
    Get daily expense totals
    Returns: List of tuples in format [(ds, y), ...]
             where ds = date string, y = total expense
    """
    query = """
    SELECT 
        DATE(created_at) as ds,
        SUM(amount) as y
    FROM transactions
    WHERE type = 'expense'
    {user_condition}
    {date_condition}
    GROUP BY ds
    ORDER BY ds
    """
    return _get_daily_financial_data(session, query, user_id, start_date, end_date)

def get_daily_income(session, user_id=None, start_date=None, end_date=None):
    """
    Get daily income totals
    Returns: List of tuples in format [(ds, y), ...]
             where ds = date string, y = total income
    """
    query = """
    SELECT 
        DATE(created_at) as ds,
        SUM(amount) as y
    FROM transactions
    WHERE type = 'income'
    {user_condition}
    {date_condition}
    GROUP BY ds
    ORDER BY ds
    """
    return _get_daily_financial_data(session, query, user_id, start_date, end_date)

def _get_daily_financial_data(session, query, user_id, start_date, end_date):
    """Helper function to execute financial queries"""
    conditions = []
    params = {}
    
    if user_id:
        conditions.append("user_id = :user_id")
        params['user_id'] = user_id
    
    if start_date and end_date:
        conditions.append("DATE(created_at) BETWEEN :start_date AND :end_date")
        params.update({'start_date': start_date, 'end_date': end_date})
    elif start_date:
        conditions.append("DATE(created_at) >= :start_date")
        params['start_date'] = start_date
    elif end_date:
        conditions.append("DATE(created_at) <= :end_date")
        params['end_date'] = end_date
    
    where_clause = "AND " + " AND ".join(conditions) if conditions else ""
    query = query.format(
        user_condition=where_clause,
        date_condition=""
    )
    
    results = execute_query(session, query, params, fetch=True)
    return [(str(date), float(amount)) for date, amount in results] if results else []

def get_financial_dataframes(session, user_id=None):
    """
    Get expense and income data as separate DataFrames
    Returns: (expense_df, income_df) with columns [ds, y]
    """
    expense_data = get_daily_expenses(session, user_id)
    income_data = get_daily_income(session, user_id)
    
    expense_df = pd.DataFrame(expense_data, columns=['ds', 'y'])
    income_df = pd.DataFrame(income_data, columns=['ds', 'y'])
    
    for df in [expense_df, income_df]:
        df['ds'] = pd.to_datetime(df['ds'])
    
    return expense_df, income_df

def get_financial_dataframes_for_manual_model(session, user_id=None):
    """
    Get expense and income data as separate DataFrames
    Returns: (expense_df, income_df) with columns [date, total_spent]
    """
    expense_data = get_daily_expenses(session, user_id)
    income_data = get_daily_income(session, user_id)
    
    expense_df = pd.DataFrame(expense_data, columns=['date', 'total_spent'])
    income_df = pd.DataFrame(income_data, columns=['date', 'total_spent'])
    
    for df in [expense_df, income_df]:
        df['date'] = pd.to_datetime(df['date'])
    
    return expense_df, income_df

def get_daily_expenses_by_category(session, user_id=None, start_date=None, end_date=None):
    """
    Get daily expense totals by category with complete date ranges
    Returns: Dictionary with categories as keys and DataFrames as values
    """
    raw_data = _get_daily_financial_data_by_category(
        session, 
        """
        SELECT 
            DATE(created_at) as ds,
            category,
            SUM(amount) as y
        FROM transactions
        WHERE type = 'expense'
        {conditions}
        GROUP BY ds, category
        ORDER BY ds, category
        """,
        user_id, 
        start_date, 
        end_date
    )
    
    return _process_category_data(raw_data, start_date, end_date)

def get_daily_income_by_category(session, user_id=None, start_date=None, end_date=None):
    """
    Get daily income totals by category with complete date ranges
    Returns: Dictionary with categories as keys and DataFrames as values
    """
    raw_data = _get_daily_financial_data_by_category(
        session, 
        """
        SELECT 
            DATE(created_at) as ds,
            category,
            SUM(amount) as y
        FROM transactions
        WHERE type = 'income'
        {conditions}
        GROUP BY ds, category
        ORDER BY ds, category
        """,
        user_id, 
        start_date, 
        end_date
    )
    
    return _process_category_data(raw_data, start_date, end_date)

def _get_daily_financial_data_by_category(session, query, user_id=None, start_date=None, end_date=None):
    """Helper function to execute financial queries with optional filters"""
    conditions = []
    params = {}
    
    if user_id is not None:
        conditions.append("user_id = :user_id")
        params['user_id'] = user_id
    
    if start_date:
        conditions.append("DATE(created_at) >= :start_date")
        params['start_date'] = start_date
    
    if end_date:
        conditions.append("DATE(created_at) <= :end_date")
        params['end_date'] = end_date
    
    where_clause = "AND " + " AND ".join(conditions) if conditions else ""
    query = query.format(conditions=where_clause)
    
    return execute_query(session, query, params, fetch=True)

def _process_category_data(raw_data, start_date, end_date):
    """Process raw category data into organized DataFrames"""
    if not raw_data:
        return {}
    
    # Get date range
    all_dates = [row[0] for row in raw_data]
    start_date = start_date or min(all_dates)
    end_date = end_date or max(all_dates)
    date_range = pd.date_range(start=start_date, end=end_date)
    
    # Organize by category
    category_dfs = {}
    all_categories = set(row[1] for row in raw_data)
    
    for category in all_categories:
        cat_data = [(row[0], row[2]) for row in raw_data if row[1] == category]
        df = pd.DataFrame(cat_data, columns=['date', 'amount'])
        df['date'] = pd.to_datetime(df['date'])
        
        full_df = pd.DataFrame({'date': date_range})
        full_df = full_df.merge(df, on='date', how='left').fillna(0)
        
        category_dfs[category] = full_df
    
    return category_dfs

def get_financial_dataframes_for_manual_model_category_extension(session, user_id=None):
    """
    Get expense and income data as separate DataFrames with categories
    Returns: (expense_df, income_df) with columns [date, total_spent, category]
    """
    expense_data = get_daily_expenses_by_category(session, user_id)
    income_data = get_daily_income_by_category(session, user_id)

    # Process expense data
    expense_rows = []
    for category, df in expense_data.items():
        for _, row in df.iterrows():
            expense_rows.append({
                'date': row['date'],
                'total_spent': float(row['amount']),
                'category': category
            })
    expense_df = pd.DataFrame(expense_rows)

    # Process income data
    income_rows = []
    for category, df in income_data.items():
        for _, row in df.iterrows():
            income_rows.append({
                'date': row['date'],
                'total_spent': float(row['amount']),
                'category': category
            })
    income_df = pd.DataFrame(income_rows)

    # Convert dates
    expense_df['date'] = pd.to_datetime(expense_df['date'])
    income_df['date'] = pd.to_datetime(income_df['date'])
    
    return expense_df, income_df