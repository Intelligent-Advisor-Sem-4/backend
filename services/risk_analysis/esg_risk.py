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

                # Calculate risk score based on ESG value ranges:
                # - <4: Negligible risk (low risk score ~1-2)
                # - 4-10: Low risk (low-medium risk score ~2-4)
                # - 10-20: Medium risk (medium risk score ~4-6)
                # - 20-30: High risk (high risk score ~6-8)
                # - >30: Severe risk (very high risk score ~8-10)
                if total_esg is not None:
                    if total_esg < 4:
                        esg_risk_score = 1.0 + (total_esg / 4)  # 1-2 range
                    elif total_esg < 10:
                        esg_risk_score = 2.0 + ((total_esg - 4) / 6) * 2  # 2-4 range
                    elif total_esg < 20:
                        esg_risk_score = 4.0 + ((total_esg - 10) / 10) * 2  # 4-6 range
                    elif total_esg < 30:
                        esg_risk_score = 6.0 + ((total_esg - 20) / 10) * 2  # 6-8 range
                    else:
                        esg_risk_score = 8.0 + min(((total_esg - 30) / 20) * 2, 2.0)  # 8-10 range, capped at 10

                    esg_risk_score = round(esg_risk_score, 2)
                else:
                    esg_risk_score = 5.0  # Neutral score when total ESG is not available

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


if __name__ == "__main__":
    # Example usage
    ticker_l = "KO"
    ticker_data_l = Ticker(ticker_l)
    esg_service = ESGDataService(ticker_l, ticker_data_l)
    esg_data_local = esg_service.get_esg_data()
    print(esg_data_local.model_dump())
