from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import numpy as np
import pandas as pd

def predict_next_day(spending_data):
    try:
        print("Predicting next day spending...", spending_data)
        
        # Ensure we have numeric data
        spending_data['total_spent'] = pd.to_numeric(spending_data['total_spent'], errors='coerce')
        data = spending_data['total_spent'].dropna().values
        
        if len(data) < 1:
            return 0.0
        
        if len(data) == 1:
            return float(data[0])
        
        # Simple exponential smoothing
        model = SimpleExpSmoothing(data).fit()
        next_day_pred = float(model.forecast(1)[0])
        
        # Adjust for day of week pattern if available
        if 'day_of_week' in spending_data.columns:
            day_of_week = spending_data['day_of_week'].iloc[-1] % 7 + 1
            day_pattern = spending_data.groupby('day_of_week')['total_spent'].mean()
            if day_of_week in day_pattern:
                final_pred = 0.7 * next_day_pred + 0.3 * day_pattern[day_of_week]
                return float(final_pred)
        
        return next_day_pred
    except Exception as e:
        print(f"Error in predict_next_day: {e}")
        if len(data) > 0:
            return float(np.mean(data))
        return 0.0

def predict_next_week(spending_data):
    try:
        print("Predicting next week spending...", spending_data)
        
        spending_data['total_spent'] = pd.to_numeric(spending_data['total_spent'], errors='coerce')
        data = spending_data['total_spent'].dropna()
        
        if len(data) == 0:
            return 0.0
        
        if 'day_of_week' in spending_data.columns:
            daily_avg = spending_data.groupby('day_of_week')['total_spent'].mean()
            if len(daily_avg) >= 7:
                return float(daily_avg.sum())
        
        if 'date' in spending_data.columns:
            weekly_totals = spending_data.resample('W', on='date')['total_spent'].sum()
            if len(weekly_totals) > 1:
                model = SimpleExpSmoothing(weekly_totals.values).fit()
                return float(model.forecast(1)[0])
        
        return float(data.mean() * 7)
    except Exception as e:
        print(f"Error in predict_next_week: {e}")
        if len(data) > 0:
            return float(data.mean() * 7)
        return 0.0

def predict_next_month(spending_data):
    try:
        print("Predicting next month spending...", spending_data)
        
        spending_data['total_spent'] = pd.to_numeric(spending_data['total_spent'], errors='coerce')
        data = spending_data['total_spent'].dropna()
        
        if len(data) == 0:
            return 0.0
        
        if 'date' in spending_data.columns:
            spending_data['day_of_month'] = spending_data['date'].dt.day
            dom_pattern = spending_data.groupby('day_of_month')['total_spent'].mean()
            
            if len(dom_pattern) >= 28:
                return float(dom_pattern.sum())
            
            if len(dom_pattern) > 0:
                current_total = dom_pattern.sum()
                projected = (current_total / len(dom_pattern)) * 30
                return float(projected)
        
        weekly_pred = predict_next_week(spending_data)
        return float(weekly_pred * 4.3)
    except Exception as e:
        print(f"Error in predict_next_month: {e}")
        if len(data) > 0:
            return float(data.mean() * 30)
        return 0.0

################

def predict_category_spending(category_dfs, period='day'):
    """
    Predict future spending/income for each category
    Returns: Dictionary of predictions for each category
    """
    print(category_dfs)
    predictions = {}
    
    for category, df in category_dfs.items():
        # Ensure data is sorted by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Convert amount to float and ensure it's numeric
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        
        # Add day of week and day of month features
        df['day_of_week'] = df['date'].dt.dayofweek + 1  # 1-7
        df['day_of_month'] = df['date'].dt.day
        
        if period == 'day':
            predictions[category] = _predict_next_day_category(df)
        elif period == 'week':
            predictions[category] = _predict_next_week_category(df)
        elif period == 'month':
            predictions[category] = _predict_next_month_category(df)
    
    return predictions

def _predict_next_day_category(df):
    """Predict next day's amount for a single category"""
    print("Predicting next day for category...", df)
    if len(df) < 2:
        return float(df['amount'].mean()) if len(df) > 0 else 0.0
    
    try:
        # Ensure data is numeric and convert to numpy array
        data = df['amount'].values.astype(float)
        
        # Simple exponential smoothing
        model = SimpleExpSmoothing(data).fit()
        next_day_pred = model.forecast(1)[0]
        
        # Adjust for day of week pattern
        day_of_week = (df['day_of_week'].iloc[-1] % 7) + 1
        day_pattern = df.groupby('day_of_week')['amount'].mean().to_dict()
        
        # Blend prediction (70% smoothing, 30% day pattern)
        final_pred = 0.7 * next_day_pred + 0.3 * day_pattern.get(day_of_week, next_day_pred)
        
        return max(0, float(final_pred))  # Ensure non-negative prediction
    except Exception as e:
        print(f"Error predicting for category: {e}")
        return float(df['amount'].mean()) if len(df) > 0 else 0.0

def _predict_next_week_category(df):
    """Predict next week's total for a single category"""
    print("Predicting next week for category...", df)
    if len(df) < 7:
        # Not enough data for weekly pattern, use daily average * 7
        return float(df['amount'].mean() * 7) if len(df) > 0 else 0.0
    
    try:
        # Calculate weekly totals
        weekly_totals = df.resample('W', on='date')['amount'].sum()
        
        if len(weekly_totals) > 1:
            # Use exponential smoothing of weekly totals
            model = SimpleExpSmoothing(weekly_totals.values.astype(float)).fit()
            return max(0, float(model.forecast(1)[0]))
        else:
            # Use sum of daily averages by day of week
            daily_avg = df.groupby('day_of_week')['amount'].mean()
            return max(0, float(daily_avg.sum()))
    except Exception as e:
        print(f"Error predicting weekly for category: {e}")
        return float(df['amount'].mean() * 7) if len(df) > 0 else 0.0

def _predict_next_month_category(df):
    """Predict next month's total for a single category"""
    print("Predicting next month for category...", df)
    if len(df) < 28:
        # Not enough data for monthly pattern
        if len(df) >= 7:
            # Use weekly prediction * 4.3
            weekly_pred = _predict_next_week_category(df)
            return max(0, float(weekly_pred * 4.3))
        else:
            # Use daily average * 30
            return max(0, float(df['amount'].mean() * 30)) if len(df) > 0 else 0.0
    
    try:
        # Calculate day-of-month patterns
        dom_pattern = df.groupby('day_of_month')['amount'].mean()
        
        if len(dom_pattern) >= 28:
            # Full month pattern available
            return max(0, float(dom_pattern.sum()))
        else:
            # Partial month - scale up
            current_month_total = dom_pattern.sum()
            projected_total = (float(current_month_total) / len(dom_pattern)) * 30
            return max(0, float(projected_total))
    except Exception as e:
        print(f"Error predicting monthly for category: {e}")
        weekly_pred = _predict_next_week_category(df)
        return max(0, float(weekly_pred * 4.3))