from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.chat_service import ChatService
from app.config import Settings
from app.database import create_database_engine
from app.main import create_app
from app.models import Base
from app.seed import seed_database

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
BUNDLE = ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json"


def _settings() -> Settings:
    return Settings(database_url="sqlite+pysqlite:///:memory:", seed_path=BUNDLE, auto_seed=True)


def _seeded_session():
    settings = _settings()
    engine = create_database_engine(settings)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    seed_database(session, settings)
    return session


def test_section_scope_grounds_on_the_section_facts() -> None:
    session = _seeded_session()
    captured: dict = {}

    def render(messages):
        captured["messages"] = messages
        return "The high-dose terminal mean is 310.7 g in males."

    chat = ChatService(session, render_fn=render)
    turn = chat.ask(STUDY_ID, "why is high-dose lower?", scope="section", section_id="5_2_3_body_weight")

    assert turn.message.role == "assistant"
    assert turn.proposed is None  # a question does not propose a rewrite
    system = captured["messages"][0]["content"]
    assert "STUDY CONTEXT" in system
    assert "CURRENT SECTION" in system
    assert "male_means" in system  # the section's verified facts are grounded


def test_chat_remembers_prior_turns() -> None:
    session = _seeded_session()
    seen: list = []

    def render(messages):
        seen.append(messages)
        return "ok"

    chat = ChatService(session, render_fn=render)
    chat.ask(STUDY_ID, "first question", scope="study")
    chat.ask(STUDY_ID, "second question", scope="study")

    # the second call replays the first turn as memory
    second_call = seen[-1]
    contents = [m["content"] for m in second_call]
    assert any("first question" in c for c in contents)
    assert len(chat.history(STUDY_ID)) == 4  # 2 user + 2 assistant


def test_edit_intent_produces_a_proposed_rewrite() -> None:
    from app.draft_service import DraftService

    session = _seeded_session()
    DraftService(session, render_fn=lambda _m: "Base narrative.").generate(
        STUDY_ID, "5_2_3_body_weight"
    )
    chat = ChatService(
        session, render_fn=lambda _m: '{"intent": "edit", "reply": "Proposed a change."}'
    )
    turn = chat.ask(STUDY_ID, "make it shorter", scope="section", section_id="5_2_3_body_weight")

    assert turn.proposed is not None
    assert turn.proposed.status == "proposed"
    assert turn.message.content  # an acknowledgement is recorded


def test_chat_endpoints(monkeypatch) -> None:
    from app import llm

    monkeypatch.setattr(llm, "chat", lambda *_a, **_k: "Grounded answer using verified data.")

    settings = _settings()
    client = TestClient(create_app(settings, create_database_engine(settings)))
    with client:
        posted = client.post(
            f"/api/v1/studies/{STUDY_ID}/chat",
            json={"message": "what is the NOAEL status?", "scope": "study", "section_id": None},
        )
        history = client.get(f"/api/v1/studies/{STUDY_ID}/chat")

    assert posted.status_code == 201
    assert posted.json()["message"]["role"] == "assistant"
    assert "verified" in posted.json()["message"]["content"]
    assert posted.json()["proposed"] is None
    assert history.status_code == 200
    assert [m["role"] for m in history.json()] == ["user", "assistant"]
