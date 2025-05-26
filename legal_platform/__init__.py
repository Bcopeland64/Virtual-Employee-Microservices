"""
AI Legal Platform Package

This package provides integration with the AI Legal Platform,
enabling AI employees to handle legal document processing,
contract analysis, compliance monitoring, and regulatory updates.

Main components:
- Document Processing: OCR and entity extraction from legal documents
- Legal Analysis: Contract review and compliance assessment
- Compliance Monitoring: Tracking regulatory changes
"""

from legal_platform.integration import DocumentProcessor, LegalAnalyzer, ComplianceMonitor

__all__ = ['DocumentProcessor', 'LegalAnalyzer', 'ComplianceMonitor']