from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field


class FinancialReportLineItem(BaseModel):
    """A single line item returned by Finnhub for a financial statement."""

    concept: str
    unit: str
    label: str
    value: float | int | None

    model_config = ConfigDict(populate_by_name=True)


class FinancialReportSection(BaseModel):
    """Aggregates balance sheet, income statement, and cash flow data."""

    bs: list[FinancialReportLineItem] = Field(default_factory=list)
    ic: list[FinancialReportLineItem] = Field(default_factory=list)
    cf: list[FinancialReportLineItem] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    def all_items(self) -> Iterable[FinancialReportLineItem]:
        """Iterate over every reported line item, regardless of section."""
        return (*self.bs, *self.ic, *self.cf)


class FinancialReportEntry(BaseModel):
    """Metadata for a single reported filing period."""

    access_number: str = Field(..., alias="accessNumber")
    symbol: str
    cik: str
    year: int
    quarter: int
    form: str
    start_date: str = Field(..., alias="startDate")
    end_date: str = Field(..., alias="endDate")
    filed_date: str = Field(..., alias="filedDate")
    accepted_date: str = Field(..., alias="acceptedDate")
    report: FinancialReportSection

    model_config = ConfigDict(populate_by_name=True)

    @property
    def income_statement(self) -> list[FinancialReportLineItem]:
        """Return the income statement portion (ic) for this period."""
        return self.report.ic


class IncomeStatementDTO(BaseModel):
    """Pydantic model representing the Finnish MCP response used in the mock data."""

    cik: str
    symbol: str
    data: list[FinancialReportEntry]

    model_config = ConfigDict(populate_by_name=True)

    def latest_income_statement(self) -> list[FinancialReportLineItem]:
        """Return the most recent income statement report, if any."""
        if not self.data:
            return []
        return self.data[0].income_statement
