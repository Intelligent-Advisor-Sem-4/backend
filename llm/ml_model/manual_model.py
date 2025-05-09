from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import numpy as np
import pandas as pd
def predict_next_day(spending_data):
    # Simple exponential smoothing
    bl = spending_data['total_spent']
    model = SimpleExpSmoothing(bl).fit()
    next_day_pred = model.forecast(1)
    
    # Adjust for day of week pattern (even with few data points)
    day_of_week = (len(spending_data) % 7) + 1  # approximate if lacking full history
    day_pattern = spending_data.groupby('day_of_week').mean().to_dict()
    
    # Blend prediction (70% smoothing, 30% day pattern)
    final_pred = 0.7 * next_day_pred + 0.3 * day_pattern.get(day_of_week, next_day_pred)
    
    return final_pred

def predict_next_week(spending_data):
    # Calculate daily averages by day of week
    daily_avg = spending_data.groupby('day_of_week')['total_spent'].mean()
    
    # If we have complete week data
    if len(daily_avg) >= 7:
        return daily_avg.sum()
    
    # For partial data, use exponential smoothing of weekly totals
    weekly_totals = spending_data.resample('W', on='date')['total_spent'].sum()
    if len(weekly_totals) > 0:
        model = SimpleExpSmoothing(weekly_totals).fit()
        return model.forecast(1)[0]
    
    # Fallback: daily average * 7
    return spending_data['total_spent'].mean() * 7

def predict_next_month(spending_data):
    # Calculate day-of-month patterns
    spending_data['day_of_month'] = spending_data['date'].dt.day
    dom_pattern = spending_data.groupby('day_of_month')['total_spent'].mean()
    
    # For full month data
    if len(dom_pattern) >= 28:
        return dom_pattern.sum()
    
    # For partial data, use ratio of available days
    current_month_days = len(dom_pattern)
    if current_month_days > 0:
        current_month_total = dom_pattern.sum()
        projected_total = (current_month_total / current_month_days) * 30
        return projected_total
    
    # Fallback: use weekly pattern * 4.3
    weekly_pred = predict_next_week(spending_data)
    return weekly_pred * 4.3

################

def predict_category_spending(category_dfs, period='day'):
    """
    Predict future spending/income for each category
    Returns: Dictionary of predictions for each category
    """
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