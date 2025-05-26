"""
AI Financial Platform Package

This package provides integration with the AI Financial Platform,
enabling AI employees to handle financial data processing,
analysis, forecasting, and risk assessment.

Main components:
- Financial Data Processing: Ingest and normalize financial data
- Financial Analysis: Analyze financial statements and cash flow
- Financial Forecasting: Generate projections and what-if scenarios
- Risk Assessment: Evaluate financial risks
- Transaction Management: Process and analyze transactions
"""

from financial_platform.integration import (
    FinancialDataProcessor,
    FinancialAnalyzer,
    FinancialForecaster,
    RiskAssessment,
    TransactionManager
)

__all__ = [
    'FinancialDataProcessor',
    'FinancialAnalyzer',
    'FinancialForecaster',
    'RiskAssessment',
    'TransactionManager'
]