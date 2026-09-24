"""Submit the repo's sample study as an upload job and poll it until it finishes."""
import io, json, sys, time, zipfile, urllib.request, uuid
from pathlib import Path
api, study_id, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
root = Path("/Users/perk/src/Helix-adosync/steven/helix-prototypes/synthetic-e2e/data")
members = sorted((root / "study_data").glob("*.csv")) + [root / "study_protocol_YZ389.docx"]
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for p in members:
        z.write(p, p.name)
payload = buf.getvalue()
boundary = uuid.uuid4().hex
fields = {"study_id": study_id, "route": "oral gavage", "protocol_version": "YZ389 v1",
          "authorized_by": "Live Acceptance (Perk bar)", "idempotency_key": f"live-{study_id}"}
body = b""
for k, v in fields.items():
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"study_YZ389.zip\"\r\n"
         "Content-Type: application/zip\r\n\r\n").encode() + payload + f"\r\n--{boundary}--\r\n".encode()
log = []
def emit(line):
    print(line); log.append(line)
emit(f"members: {[p.name for p in members]} zip_bytes={len(payload)}")
req = urllib.request.Request(f"{api}/studies/jobs", data=body, method="POST",
                             headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
t0 = time.perf_counter()
with urllib.request.urlopen(req) as r:
    job = json.load(r); emit(f"POST /studies/jobs -> {r.status}")
emit(f"t=+{(time.perf_counter()-t0)*1000:7.1f}ms status={job['status']:9} stage={job.get('stage')} stages_done={list(job.get('stages',{}))}")
last = (job["status"], job.get("stage"), tuple(job.get("stages", {})))
while job["status"] in ("queued", "running"):
    time.sleep(0.005)
    with urllib.request.urlopen(f"{api}/studies/jobs/{job['job_id']}") as r:
        job = json.load(r)
    cur = (job["status"], job.get("stage"), tuple(job.get("stages", {})))
    if cur != last:
        emit(f"t=+{(time.perf_counter()-t0)*1000:7.1f}ms status={job['status']:9} stage={job.get('stage')} stages_done={list(job.get('stages',{}))}")
        last = cur
emit("final job record:"); emit(json.dumps(job, indent=2))
out.write_text("\n".join(log) + "\n")
