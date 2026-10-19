"""Postgres (Supabase) repository layer -- additive read-only content-bank
access sitting alongside the existing Mongo code, not replacing it yet.

Each module here mirrors the query SHAPES the equivalent Mongo-based module
(backend/banks/*.py, backend/games/gamified_round.py, backend/server.py's
capgemini_round1_bank/capgemini_round2_bank reads) already uses, so a later
cutover phase can swap the data source underneath an unchanged call site
without redesigning what callers are allowed to ask for. See
SUPABASE_MIGRATION_BRIEF.md for the overall plan; nothing in this package is
wired into server.py yet.
"""
