from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import create_database_engine
from app.draft_service import DraftService, structured_tables
from app.main import create_app
from app.section_executor import run_section
from app.seed import load_seed_package, resolve_seed_path

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "STUDY-HLX-028"
BUNDLE = ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json"


def _settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        seed_path=BUNDLE,
        auto_seed=True,
    )


def build_client() -> TestClient:
    settings = _settings()
    engine = create_database_engine(settings)
    return TestClient(create_app(settings, engine))


def _seeded_session():
    settings = _settings()
    engine = create_database_engine(settings)
    from app.models import Base
    from app.seed import seed_database

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    seed_database(session, settings)
    return session


# --- deterministic: tables come from verified data, no LLM ------------------ #

def test_body_weight_tables_are_built_from_verified_facts() -> None:
    package = load_seed_package(resolve_seed_path(BUNDLE))
    result = run_section("5_2_3_body_weight", package)
    tables = structured_tables(result)

    assert [t["title"] for t in tables] == [
        "Male mean body weight (g)",
        "Female mean body weight (g)",
    ]
    male = tables[0]
    assert male["columns"] == ["Group", "Day 1", "Day 7", "Day 14", "Day 21", "Day 28"]
    assert len(male["rows"]) == 4  # four dose groups
    # G4 (high dose) terminal male mean is the verified 310.7 g
    g4 = next(row for row in male["rows"] if row[0].startswith("G4"))
    assert g4[-1] == "310.7"


def test_generate_uses_injected_render_and_stays_needs_review() -> None:
    session = _seeded_session()
    service = DraftService(session, render_fn=lambda messages: "Body weight was comparable across groups.")
    draft = service.generate(STUDY_ID, "5_2_3_body_weight")

    assert draft.status == "needs_review"
    assert draft.data_available is True
    assert draft.version == 1
    assert draft.provenance_count == 40
    kinds = [b.kind for b in draft.blocks]
    assert kinds == ["prose", "table", "table"]
    assert draft.blocks[0].markdown.startswith("Body weight was comparable")


def test_feedback_is_carried_into_the_render_prompt() -> None:
    session = _seeded_session()
    captured: dict = {}

    def render(messages):
        captured["messages"] = messages
        return "revised prose"

    service = DraftService(session, render_fn=render)
    service.generate(STUDY_ID, "5_2_3_body_weight")  # v1 (anchor)
    service.generate(STUDY_ID, "5_2_3_body_weight", feedback=["mention % vs control"])  # v2

    user_turn = captured["messages"][1]["content"]
    assert "REVIEWER FEEDBACK" in user_turn
    assert "mention % vs control" in user_turn
    assert "CURRENT DRAFT" in user_turn  # anchored to the previous draft


def test_no_data_section_is_needs_review_note_without_tables() -> None:
    session = _seeded_session()
    service = DraftService(session, render_fn=lambda messages: "should not be called")
    draft = service.generate(STUDY_ID, "5_3_4_conclusion")

    assert draft.data_available is False
    assert [b.kind for b in draft.blocks] == ["note"]
    assert "NEEDS REVIEW" in draft.blocks[0].text


# --- endpoints -------------------------------------------------------------- #

def test_sections_endpoint_lists_fourteen() -> None:
    client = build_client()
    with client:
        response = client.get(f"/api/v1/studies/{STUDY_ID}/sections")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 14
    assert items[0]["status"] == "empty"


def test_draft_endpoint_degrades_without_a_model() -> None:
    client = build_client()
    with client:
        created = client.post(
            f"/api/v1/studies/{STUDY_ID}/sections/5_2_3_body_weight/draft",
            json={"feedback": []},
        )
        fetched = client.get(f"/api/v1/studies/{STUDY_ID}/sections/5_2_3_body_weight/draft")
        unknown = client.post(
            f"/api/v1/studies/{STUDY_ID}/sections/not_a_section/draft",
            json={"feedback": []},
        )

    assert created.status_code == 201
    body = created.json()
    # No APIM configured -> prose degrades to a note, but verified tables remain.
    assert [b["kind"] for b in body["blocks"]] == ["note", "table", "table"]
    assert fetched.status_code == 200
    assert fetched.json()["version"] == 1
    assert unknown.status_code == 404
