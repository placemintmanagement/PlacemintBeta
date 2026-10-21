"""Unit tests for games/gamified_round.py's DB_BACKEND dispatch
(SUPABASE_CUTOVER_PLAN.md Step 1) -- confirms get_config()/sample_puzzles()/
check_answer()/grade_session() call the right repositories/puzzle_bank_pg.py
function under DB_BACKEND=supabase, that game_session (repetition-tracking,
live_checks, grading) keeps going through the SAME Mongo fake regardless of
backend, and that the DEFAULT (DB_BACKEND unset) still runs the exact
original Mongo-fake path untouched."""
from __future__ import annotations

import asyncio

import pytest

from games import gamified_round
from repositories import puzzle_bank_pg


class _FakeGameSessionCollection:
    def __init__(self, sessions=None):
        self.sessions = sessions or {}
        self.update_calls = []

    async def find_one(self, query):
        return self.sessions.get(query["session_id"])

    async def update_one(self, filter_, update, upsert=False):
        self.update_calls.append((filter_, update))
        sid = filter_["session_id"]
        doc = self.sessions.setdefault(sid, {"session_id": sid})
        doc.update(update.get("$set", {}))


class _FakePuzzleBankCollection:
    def __init__(self, docs):
        self.docs = {d["puzzle_id"]: d for d in docs}

    async def find_one(self, query, projection=None):
        return self.docs.get(query.get("puzzle_id"))

    def find(self, query, projection=None):
        ids = set(query.get("puzzle_id", {}).get("$in", []))
        return _FakeCursor([d for pid, d in self.docs.items() if pid in ids])


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs[:length] if length is not None else list(self._docs)


class _FakeDb:
    def __init__(self, puzzle_docs=None, sessions=None, config_docs=None):
        self.puzzle_bank = _FakePuzzleBankCollection(puzzle_docs or [])
        self.game_session = _FakeGameSessionCollection(sessions)
        self._config_docs = {d["company"]: d for d in (config_docs or [])}

    @property
    def gamified_round_config(self):
        db = self

        class _Cfg:
            async def find_one(self, query, projection=None):
                return db._config_docs.get(query.get("company"))

        return _Cfg()


PUZZLE = {
    "puzzle_id": "pz1", "gameType": "deductive_grid", "companyTags": ["TCS"],
    "correctAnswer": 2, "explanation": "because", "grid": [[1, 2], [3, 4]],
}


@pytest.fixture(autouse=True)
def _reset_db():
    yield
    gamified_round._db = None


def test_get_config_mongo_default_unchanged(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    gamified_round._db = _FakeDb(config_docs=[{"company": "TCS", "drawCount": 4}])
    cfg = asyncio.run(gamified_round.get_config("TCS"))
    assert cfg == {"company": "TCS", "drawCount": 4}


def test_get_config_supabase_dispatches_to_repo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    gamified_round._db = _FakeDb()

    async def fake_get_config(company):
        assert company == "TCS"
        return {"company": "TCS", "drawCount": 4, "gameTypes": ["deductive_grid"], "perType": {}, "_drawNote": None}

    monkeypatch.setattr(puzzle_bank_pg, "get_config", fake_get_config)
    cfg = asyncio.run(gamified_round.get_config("TCS"))
    assert cfg["drawCount"] == 4


def test_check_answer_supabase_dispatches_to_repo_get_by_id(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    gamified_round._db = _FakeDb(
        puzzle_docs=[], sessions={"att1_games": {"session_id": "att1_games", "live_checks": {}, "running_score": 0}},
    )

    async def fake_get_by_id(puzzle_id):
        assert puzzle_id == "pz1"
        return dict(PUZZLE)

    monkeypatch.setattr(puzzle_bank_pg, "get_by_id", fake_get_by_id)
    result = asyncio.run(gamified_round.check_answer("att1", "games", "pz1", 2))
    assert result["correct"] is True
    assert "correctAnswer" not in result and "explanation" not in result


def test_grade_session_supabase_dispatches_to_repo_get_by_ids(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    gamified_round._db = _FakeDb(
        puzzle_docs=[],
        sessions={"att1_games": {"session_id": "att1_games", "puzzleIdsByType": {"deductive_grid": ["pz1"]}}},
    )

    async def fake_get_by_ids(puzzle_ids):
        assert puzzle_ids == ["pz1"]
        return [dict(PUZZLE)]

    monkeypatch.setattr(puzzle_bank_pg, "get_by_ids", fake_get_by_ids)
    result = asyncio.run(
        gamified_round.grade_session("att1_games", "deductive_grid", {"pz1": {"selected": 2}})
    )
    assert result["total"] == 1
    assert result["correct"] == 1


def test_sample_puzzles_supabase_dispatches_to_repo_with_seen_from_mongo(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "supabase")
    gamified_round._db = _FakeDb(
        puzzle_docs=[],
        sessions={},
    )
    # get_seen_puzzle_ids reads _db.game_session.find() (an async iterator),
    # not find_one -- patch it directly since _FakeGameSessionCollection
    # above doesn't implement the cursor-style .find() used there.
    async def fake_get_seen(user_id, game_type):
        return {"pz_seen"}

    monkeypatch.setattr(gamified_round, "get_seen_puzzle_ids", fake_get_seen)

    captured = {}

    async def fake_sample_puzzles(company, game_type, exclude_ids, count):
        captured["args"] = (company, game_type, exclude_ids, count)
        return [dict(PUZZLE)]

    monkeypatch.setattr(puzzle_bank_pg, "sample_puzzles", fake_sample_puzzles)
    out = asyncio.run(gamified_round.sample_puzzles("TCS", "deductive_grid", "u1", 3))
    assert captured["args"][0:2] == ("TCS", "deductive_grid")
    assert set(captured["args"][2]) == {"pz_seen"}
    assert captured["args"][3] == 3
    assert "correctAnswer" not in out[0], "strip_answer must still run on the supabase path"
