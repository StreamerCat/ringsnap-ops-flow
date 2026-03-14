"""
Supabase adapter — wraps supabase-py with retry and error normalization.
Protected: changes here affect all DB reads/writes in the ops flow.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import BaseAdapter

logger = logging.getLogger(__name__)


class SupabaseAdapter(BaseAdapter):
    """
    Thin wrapper around supabase-py client.
    Provides query/upsert interface used by all deterministic services.
    """

    def __init__(self, url: str = "", key: str = ""):
        stub = not (url and key)
        super().__init__(stub=stub)
        self._client = None
        if not stub:
            try:
                from supabase import create_client
                self._client = create_client(url, key)
                logger.info("supabase_adapter.connected url=%s", url[:30])
            except Exception as e:
                logger.error("supabase_adapter.connection_failed error=%s", e)
                self._stub = True

    def query(self, table: str, filters: Optional[dict] = None) -> list[dict[str, Any]]:
        """
        Query a table with optional filters dict.
        Filter format: {"column": "eq.value"} (PostgREST style)
        Returns list of rows.
        """
        if self.is_stub:
            self._log_stub("query", table=table, filters=filters)
            return []

        try:
            q = self._client.table(table).select("*")
            if filters:
                for col, val in filters.items():
                    # Parse PostgREST-style filters
                    if "." in val:
                        op, v = val.split(".", 1)
                        if op == "eq":
                            q = q.eq(col, v)
                        elif op == "gte":
                            q = q.gte(col, v)
                        elif op == "lte":
                            q = q.lte(col, v)
                        elif op == "neq":
                            q = q.neq(col, v)
                        elif op == "in":
                            q = q.in_(col, v.strip("()").split(","))
                    else:
                        q = q.eq(col, val)
            result = q.execute()
            return result.data or []
        except Exception as e:
            logger.error("supabase_adapter.query_failed table=%s error=%s", table, e)
            return []

    def upsert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Upsert a single record. Uses id field for conflict resolution if present.
        Returns the upserted row.
        """
        if self.is_stub:
            self._log_stub("upsert", table=table, data=data)
            return data

        try:
            result = self._client.table(table).upsert(data).execute()
            rows = result.data or []
            return rows[0] if rows else data
        except Exception as e:
            logger.error("supabase_adapter.upsert_failed table=%s error=%s", table, e)
            raise

    def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new record. Raises on conflict."""
        if self.is_stub:
            self._log_stub("insert", table=table, data=data)
            return data

        try:
            result = self._client.table(table).insert(data).execute()
            rows = result.data or []
            return rows[0] if rows else data
        except Exception as e:
            logger.error("supabase_adapter.insert_failed table=%s error=%s", table, e)
            raise

    def rpc(self, function_name: str, params: Optional[dict] = None) -> Any:
        """Call a Supabase RPC function."""
        if self.is_stub:
            self._log_stub("rpc", function=function_name, params=params)
            return None

        try:
            result = self._client.rpc(function_name, params or {}).execute()
            return result.data
        except Exception as e:
            logger.error("supabase_adapter.rpc_failed fn=%s error=%s", function_name, e)
            raise
