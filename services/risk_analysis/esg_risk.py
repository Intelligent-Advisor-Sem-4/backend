from yfinance import Ticker
from classes.Risk_Components import EsgRiskResponse


class ESGDataService:
    def __init__(self, ticker: str, ticker_data: Ticker):
        self.ticker_data = ticker_data
        self.ticker = ticker

    def get_esg_data(self) -> EsgRiskResponse:
        """Get ESG (Environmental, Social, Governance) risk data"""
        print("Getting ESG data")
        try:
            # Try to get ESG data from yfinance
            esg_data = self.ticker_data.sustainability

            if esg_data is not None and not esg_data.empty:
                # Extract ESG scores - proper DataFrame indexing
                # Note: sustainability returns a DataFrame with a single column
                # The values we want are in the first row, accessed via .iloc[0]
                total_esg = esg_data.loc['totalEsg'].iloc[0] if 'totalEsg' in esg_data.index else None
                env_score = esg_data.loc['environmentScore'].iloc[
                    0] if 'environmentScore' in esg_data.index else None
                social_score = esg_data.loc['socialScore'].iloc[0] if 'socialScore' in esg_data.index else None
                governance_score = esg_data.loc['governanceScore'].iloc[
                    0] if 'governanceScore' in esg_data.index else None

                # Calculate risk score from ESG (higher ESG risk = higher risk score)
                esg_risk_score = 10 - (total_esg / 10) if total_esg is not None else 5

                # Return data as Pydantic model
                return EsgRiskResponse(
                    total_esg=total_esg,
                    environmental_score=env_score,
                    social_score=social_score,
                    governance_score=governance_score,
                    esg_risk_score=float(esg_risk_score)
                )
            else:
                # Return default model with neutral risk score when data not available
                return EsgRiskResponse(
                    esg_risk_score=5.0  # Neutral score when data not available
                )
        except Exception as e:
            print(f"Error getting ESG data: {e}")
            # Return default model with neutral risk score on error
            return EsgRiskResponse(esg_risk_score=5.0)