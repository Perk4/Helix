#!/bin/bash
# usage: run-spec.sh REPO_ROOT OUT_DIR
R=$1; OUT=$2
rm -rf "$OUT"; mkdir -p "$OUT"
cp /tmp/live/zz-live-acceptance.spec.ts $R/frontend/tests/
cd $R/frontend && LIVE_OUT=$OUT HELIX_WEB_URL=http://127.0.0.1:3010 HELIX_API_URL=http://127.0.0.1:8010/api/v1 npx playwright test tests/zz-live-acceptance.spec.ts 2>&1 | grep -E "passed|failed|✓|✘"
rm -f $R/frontend/tests/zz-live-acceptance.spec.ts
python3 - "$OUT/result.json" <<'PY'
import json,re,sys; d=json.load(open(sys.argv[1]))
if "stop" in d: d["stop"]["error"]=re.sub(r"\x1b\[[0-9;]*m","",d["stop"]["error"])
json.dump(d,open(sys.argv[1],"w"),indent=2); print(json.dumps(d,indent=2))
PY
