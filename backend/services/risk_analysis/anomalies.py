from datetime import datetime, timedelta
from typing import List

import pandas as pd
from yfinance import Ticker

from classes.Risk_Components import AnomalyDetectionResponse, AnomalyFlag, HistoricalDataPoint


class AnomalyDetectionService:
    def __init__(self, ticker: str, ticker_data: Ticker):
        self.ticker = ticker
        self.ticker_data = ticker_data

    def detect_anomalies(self, lookback_days: int = 30) -> AnomalyDetectionResponse:
        """Detect price, volume and other anomalies"""
        print("Detect anomalies")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        try:
            # Get historical data
            hist = self.ticker_data.history(start=start_date, end=end_date)
            if hist.empty:
                return AnomalyDetectionResponse(flags=[], anomaly_score=0, historical_data=[])

            flags: List[AnomalyFlag] = []
            flag_scores = []

            # 1. Check for unusual price gaps
            daily_changes = hist['Close'].pct_change().dropna()

            # Hybrid approach: Use both standard deviation and absolute threshold
            # Standard deviation for moderate anomalies
            std_change = daily_changes.std()

            # For extreme outliers that would skew standard deviation, use absolute threshold
            major_outliers = daily_changes[abs(daily_changes) > 0.15]  # 15% absolute threshold

            # For moderate outliers, use standard deviation if we have enough data points
            if len(daily_changes) >= 10:
                # First identify and remove extreme outliers for calculating std
                q1, q3 = daily_changes.quantile(0.25), daily_changes.quantile(0.75)
                iqr = q3 - q1
                clean_changes = daily_changes[(daily_changes >= q1 - 1.5 * iqr) & (daily_changes <= q3 + 1.5 * iqr)]
                std_change = clean_changes.std() if not clean_changes.empty else daily_changes.std()
                moderate_outliers = daily_changes[
                    (abs(daily_changes) > 3 * std_change) & (abs(daily_changes) <= 0.15)]
                unusual_changes = pd.concat([major_outliers, moderate_outliers])
            else:
                # With limited data points, rely on the fixed threshold
                unusual_changes = major_outliers

            for date, change in unusual_changes.items():
                # Calculate severity based on the magnitude of the change
                severity = min(10, abs(change) * 10)  # 40% change would be severity 4
                flag_scores.append(severity)

                # Determine if this is a statistical anomaly or a major price move
                if abs(change) > 0.15:
                    description = f"Major price change of {change * 100:.2f}%"
                else:
                    description = f"Statistically unusual price change of {change * 100:.2f}% (over 3σ)"

                flags.append(AnomalyFlag(
                    type="Price Gap",
                    date=date.strftime("%Y-%m-%d"),
                    description=description,
                    severity=float(severity)
                ))

            # 2. Check for unusual volume spikes
            volume_mean = hist['Volume'].mean()
            volume_std = hist['Volume'].std()
            unusual_volume = hist[hist['Volume'] > volume_mean + 2 * volume_std]

            for date, row in unusual_volume.iterrows():
                volume_ratio = row['Volume'] / volume_mean
                severity = min(10, (volume_ratio - 1) / 2)
                flag_scores.append(severity)
                flags.append(AnomalyFlag(
                    type="Volume Spike",
                    date=date.strftime("%Y-%m-%d"),
                    description=f"Volume {volume_ratio:.1f}x above average",
                    severity=float(severity)
                ))

            # 3. Check for bearish patterns (e.g., consecutive down days)
            price_changes = hist['Close'].pct_change().dropna()
            down_days = (price_changes < 0).astype(int)
            bearish_runs = down_days.rolling(window=5).sum()

            if bearish_runs.max() >= 4:  # 4+ down days in a 5-day window
                severity = min(10, bearish_runs.max() * 2)
                flag_scores.append(severity)
                flags.append(AnomalyFlag(
                    type="Bearish Pattern",
                    date=bearish_runs.idxmax().strftime("%Y-%m-%d"),
                    description=f"{int(bearish_runs.max())} down days in a 5-day window",
                    severity=float(severity)
                ))

            # Calculate anomaly score
            anomaly_score = max(flag_scores) if flag_scores else 0
            if len(flags) > 3:  # If there are multiple anomalies
                anomaly_score = min(10.0, anomaly_score * (1 + 0.1 * (len(flags) - 3)))

            # Create historical data points for frontend plotting
            historical_data = []
            for date, row in hist.iterrows():
                historical_data.append(HistoricalDataPoint(
                    date=date.strftime("%Y-%m-%d"),
                    close=float(row['Close']),
                    volume=float(row['Volume']),
                    percent_change=float(daily_changes.get(date, 0))
                ))

            return AnomalyDetectionResponse(
                flags=flags,
                anomaly_score=float(anomaly_score),
                historical_data=historical_data
            )
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            return AnomalyDetectionResponse(flags=[], anomaly_score=0, historical_data=[])
