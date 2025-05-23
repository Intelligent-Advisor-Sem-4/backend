from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, JSON, Date, ForeignKey, Numeric, BigInteger, \
    Text
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import enum
import uuid

Base = declarative_base()


# Create an enum class for access levels
class AccessLevel(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNDEFINED = "undefined"


class AssetStatus(enum.Enum):
    PENDING = "Pending"  # Symbol added but model not trained
    ACTIVE = "Active"  # Model trained; available for prediction and portfolios
    WARNING = "Warning"  # Shows in dashboards but excluded from portfolios
    BLACKLIST = "BlackList"  # Hidden from everything


class AssetStatus(enum.Enum):
    PENDING = "Pending"  # Symbol added but model not trained
    ACTIVE = "Active"  # Model trained; available for prediction and portfolios
    WARNING = "Warning"  # Shows in dashboards but excluded from portfolios
    BLACKLIST = "BlackList"  # Hidden from everything


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    birthday = Column(DateTime, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    access_level = Column(Enum(AccessLevel), default=AccessLevel.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Stock(Base):
    """Model representing a tradable financial asset (stock, crypto, etc.)"""

    __tablename__ = "stocks"

    stock_id = Column(Integer, primary_key=True)
    ticker_symbol = Column(String(20), unique=True, nullable=False)
    asset_name = Column(String(255))
    currency = Column(String(10), default="USD")
    exchange = Column(String(50), nullable=True)  # Made optional
    sectorKey = Column(String(50), nullable=True)  # Made optional
    sectorDisp = Column(String(50), nullable=True)  # Made optional
    industryKey = Column(String(50), nullable=True)  # Made optional
    industryDisp = Column(String(50), nullable=True)  # Made optional
    timezone = Column(String(50), nullable=True)  # Made optional
    status = Column(Enum(AssetStatus), nullable=False, default=AssetStatus.PENDING)
    type = Column(String(50), nullable=True)  # Made optional
    first_data_point_date = Column(Date, nullable=True)
    last_data_point_date = Column(Date, nullable=True)
    risk_score = Column(Numeric(10, 2), nullable=True)
    risk_score_updated = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- Relationships ---
    historical_prices = relationship("StockPriceHistorical", back_populates="stock", cascade="all, delete-orphan")
    prediction_models = relationship("PredictionModel", back_populates="target_stock")
    news_risk_analysis = relationship("NewsRiskAnalysis", back_populates="stock", cascade="all, delete-orphan")
    quantitative_risk_analysis = relationship("QuantitativeRiskAnalysis", back_populates="stock",
                                              cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stock(stock_id={self.stock_id}, ticker_symbol='{self.ticker_symbol}', type='{self.type}')>"


class StockPriceHistorical(Base):
    """Model for stock_price_historical table"""
    __tablename__ = "stock_price_historical"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.stock_id", ondelete="CASCADE"))
    price_date = Column(DateTime)
    open_price = Column(Numeric(19, 4))
    high_price = Column(Numeric(19, 4))
    low_price = Column(Numeric(19, 6))
    close_price = Column(Numeric(19, 6))
    volume = Column(BigInteger)
    fetched_at = Column(DateTime(timezone=True), default=func.now())

    # Relationship
    stock = relationship("Stock", back_populates="historical_prices")

    def __repr__(self):
        return f"<StockPriceHistorical(stock_id={self.stock_id}, date='{self.price_date}', close={self.close_price})>"


class PredictionModel(Base):
    """Model for prediction_models table"""
    __tablename__ = "prediction_models"

    model_id = Column(Integer, primary_key=True)
    model_version = Column(String(100), nullable=False)
    target_stock_id = Column(Integer, ForeignKey("stocks.stock_id", ondelete="SET NULL"), nullable=True)
    latest_modified_time = Column(DateTime(timezone=True), default=func.now())
    time_step = Column(Integer)
    rmse = Column(Numeric(10, 7))
    is_active = Column(Boolean, default=True)
    model_location = Column(Text)
    scaler_location = Column(Text)
    trained_upto_date = Column(Date, nullable=True)
    data_points = Column(Integer, nullable=False)

    # Relationships
    target_stock = relationship("Stock", back_populates="prediction_models")
    predictions = relationship("StockPrediction", back_populates="model")

    def __repr__(self):
        return f"<PredictionModel(model_id={self.model_id}, version='{self.model_version}', active={self.is_active})>"


class StockPrediction(Base):
    """Model for stock_predictions table"""
    __tablename__ = "stock_predictions"

    prediction_id = Column(BigInteger, primary_key=True)
    model_id = Column(Integer, ForeignKey("prediction_models.model_id", ondelete="SET NULL"), nullable=True)
    prediction_generated_at = Column(DateTime(timezone=True), default=func.now())
    last_actual_data_date = Column(Date, nullable=False)
    predicted_date = Column(Date, nullable=False)
    predicted_price = Column(Numeric(19, 4))
    confidence_score = Column(Numeric(19, 4), nullable=False)

    # Relationship
    model = relationship("PredictionModel", back_populates="predictions")

    def __repr__(self):
        return f"<StockPrediction(id={self.prediction_id}, date='{self.predicted_date}', price={self.predicted_price})>"


class NewsRiskAnalysis(Base):
    __tablename__ = "news_risk_analysis"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.stock_id", ondelete="CASCADE"), nullable=False)

    response_json = Column(JSON, nullable=True)
    stability_score = Column(Numeric(10, 2), nullable=True)
    stability_label = Column(String(50), nullable=True)
    customer_suitability = Column(String(50), nullable=True)
    suggested_action = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())
    risk_score = Column(Numeric(10, 2), nullable=True)

    stock = relationship("Stock", back_populates="news_risk_analysis")


from sqlalchemy import Text


class QuantitativeRiskAnalysis(Base):
    __tablename__ = "quantitative_risk_analysis"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    volatility = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    rsi = Column(Numeric(10, 4), nullable=True)
    volume_change = Column(Numeric(10, 4), nullable=True)
    debt_to_equity = Column(Numeric(10, 4), nullable=True)
    eps = Column(Numeric(10, 4), nullable=True)
    stock_id = Column(Integer, ForeignKey("stocks.stock_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

    response = Column(JSONB, nullable=True)

    stock = relationship("Stock", back_populates="quantitative_risk_analysis")

    def __repr__(self):
        return f"<QuantitativeRiskAnalysis(analysis_id={self.analysis_id}, volatility={self.volatility})>"


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class BudgetGoal(Base):
    __tablename__ = "budget_goal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)

    # Changed from "users" to UserModel
    user = relationship("UserModel", backref=backref("budget_goal", lazy="dynamic"))

    def __repr__(self):
        return f"<BudgetGoal(id={self.id}, title='{self.title}', amount={self.amount})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    type = Column(Enum(TransactionType), nullable=False)
    reason = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Changed from "users" to UserModel
    user = relationship("UserModel", backref=backref("transactions", lazy="dynamic"))

    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.type}', amount={self.amount})>"


class RiskAnalysis(Base):
    __tablename__ = "risk_level"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    risk_score = Column(Numeric(10, 2), nullable=False)

    user = relationship("UserModel", backref=backref("risk_analysis", lazy="dynamic"))
