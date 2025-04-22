from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, JSON, Date, ForeignKey, Numeric, BigInteger, \
    Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
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


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    birthday = Column(DateTime, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    access_level = Column(Enum(AccessLevel), default=AccessLevel.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


## Models for Stock Price Prediction ##############################################################
class Stock(Base):
    """Model for stocks table"""
    __tablename__ = "stocks"

    stock_id = Column(Integer, primary_key=True)
    ticker_symbol = Column(String(20), unique=True, nullable=False)
    company_name = Column(String(255))
    currency = Column(String(10), default="USD")
    is_active = Column(Boolean, default=True)
    first_data_point_date = Column(Date)
    last_data_point_date = Column(Date)

    # Relationships
    historical_prices = relationship("StockPriceHistorical", back_populates="stock", cascade="all, delete-orphan")
    prediction_models = relationship("PredictionModel", back_populates="target_stock")

    def __repr__(self):
        return f"<Stock(stock_id={self.stock_id}, ticker_symbol='{self.ticker_symbol}')>"


class StockPriceHistorical(Base):
    """Model for stock_price_historical table"""
    __tablename__ = "stock_price_historical"

    stock_id = Column(Integer, ForeignKey("stocks.stock_id", ondelete="CASCADE"), primary_key=True)
    price_date = Column(Date, primary_key=True)
    open_price = Column(Numeric(19, 4))
    high_price = Column(Numeric(19, 4))
    low_price = Column(Numeric(19, 4))
    close_price = Column(Numeric(19, 4))
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

    # Relationship
    model = relationship("PredictionModel", back_populates="predictions")

    def __repr__(self):
        return f"<StockPrediction(id={self.prediction_id}, date='{self.predicted_date}', price={self.predicted_price})>"


class RiskModel(Base):
    __tablename__ = 'risk_models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    version = Column(String)
    description = Column(String)
    parameters = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, onupdate=datetime.utcnow)


class ExplainabilityReport(Base):
    __tablename__ = 'explainability_reports'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer)
    model_id = Column(Integer)
    report_data = Column(JSON)  # Stores SHAP values, LIME explanations, etc.
    generated_at = Column(DateTime, default=datetime.utcnow)
    explanation_type = Column(String)  # e.g., "SHAP", "LIME", "Gemini"
