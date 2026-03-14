"""CrewAI tool for querying Supabase from within crew tasks."""

from __future__ import annotations

from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SupabaseQueryInput(BaseModel):
    table: str = Field(description="Supabase table name to query")
    filters: Optional[dict] = Field(default=None, description="Filter dict in PostgREST style")
    limit: int = Field(default=50, description="Max rows to return")


class SupabaseQueryTool(BaseTool):
    """Query Supabase database tables. Use for looking up account state, pending signups, etc."""

    name: str = "supabase_query"
    description: str = "Query Supabase database. Returns rows from the specified table with optional filters."
    args_schema: Type[BaseModel] = SupabaseQueryInput

    # Injected by the flow — not a Pydantic field on the tool model
    _supabase: Any = None

    def _run(self, table: str, filters: Optional[dict] = None, limit: int = 50) -> str:
        if self._supabase is None:
            return "[stub] No Supabase adapter configured. Returning empty result."
        rows = self._supabase.query(table, filters)
        return str(rows[:limit])
