"""Run the deterministic section executor on a stored package read back from PostgreSQL."""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.repository import StudyPackageRepository
from app.section_executor import run_all
url, study_id = sys.argv[1], sys.argv[2]
with Session(create_engine(url)) as session:
    package = StudyPackageRepository(session).get(study_id)
print(f"section executor on {study_id} (records read from PostgreSQL):")
for r in run_all(package):
    keys = list(r.facts)[:4]
    print(f"  {r.section_id:22} data_available={str(r.data_available):5} facts={len(r.facts):2} provenance={len(r.provenance):3} keys={keys}")
bw = next(r for r in run_all(package) if r.section_id == "5_2_3_body_weight")
print("  5_2_3_body_weight sample provenance:", bw.provenance[0] if bw.provenance else None)
