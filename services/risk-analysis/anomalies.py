from datetime import datetime, timedelta
from typing import Dict, Any

from yfinance import Ticker


class AnomalyDetectionService:
    def __init__(self, ticker: str, ticker_data: Ticker):
        self.ticker = ticker
        self.ticker_data = ticker_data

    def detect_anomalies(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Detect price, volume and other anomalies"""
        print("Detect anomalies")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        try:
            # Get historical data
            hist = self.ticker_data.history(start=start_date, end=end_date)
            if hist.empty:
                return {"flags": [], "anomaly_score": 0}

            flags = []
            flag_scores = []

            # 1. Check for unusual price gaps
            daily_changes = hist['Close'].pct_change().dropna()
            std_change = daily_changes.std()
            unusual_changes = daily_changes[abs(daily_changes) > 3 * std_change]

            for date, change in unusual_changes.items():
                severity = min(10, abs(change) / std_change)
                flag_scores.append(severity)
                flags.append({
                    "type": "Price Gap",
                    "date": date.strftime("%Y-%m-%d"),
                    "description": f"Unusual price change of {change * 100:.2f}% (over 3σ)",
                    "severity": float(severity)
                })

            # 2. Check for unusual volume spikes
            volume_mean = hist['Volume'].mean()
            volume_std = hist['Volume'].std()
            unusual_volume = hist[hist['Volume'] > volume_mean + 2 * volume_std]

            for date, row in unusual_volume.iterrows():
                volume_ratio = row['Volume'] / volume_mean
                severity = min(10, (volume_ratio - 1) / 2)
                flag_scores.append(severity)
                flags.append({
                    "type": "Volume Spike",
                    "date": date.strftime("%Y-%m-%d"),
                    "description": f"Volume {volume_ratio:.1f}x above average",
                    "severity": float(severity)
                })

            # 3. Check for bearish patterns (e.g., consecutive down days)
            price_changes = hist['Close'].pct_change().dropna()
            down_days = (price_changes < 0).astype(int)
            bearish_runs = down_days.rolling(window=5).sum()

            if bearish_runs.max() >= 4:  # 4+ down days in a 5-day window
                severity = min(10, bearish_runs.max() * 2)
                flag_scores.append(severity)
                flags.append({
                    "type": "Bearish Pattern",
                    "date": bearish_runs.idxmax().strftime("%Y-%m-%d"),
                    "description": f"{int(bearish_runs.max())} down days in a 5-day window",
                    "severity": float(severity)
                })

            # Calculate anomaly score
            anomaly_score = max(flag_scores) if flag_scores else 0
            if len(flags) > 3:  # If there are multiple anomalies
                anomaly_score = min(10.0, anomaly_score * (1 + 0.1 * (len(flags) - 3)))

            return {
                "flags": flags,
                "anomaly_score": float(anomaly_score)
            }
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            return {"flags": [], "anomaly_score": 0}
