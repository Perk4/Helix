#!/bin/bash
# usage: pre-alembic.sh pg|sqlite
KIND=$1; R=/Users/perk/src/Helix-adosync/steven/helix-prototypes; B=/Users/perk/src/Helix-base-f577/steven/helix-prototypes
if [ $KIND = pg ]; then
  dropdb --if-exists -h 127.0.0.1 -p 55441 -U helix helix_pre; createdb -h 127.0.0.1 -p 55441 -U helix helix_pre
  URL=postgresql+psycopg://helix@127.0.0.1:55441/helix_pre; C="pg helix_pre"
else
  rm -f /tmp/live/pre.db; URL=sqlite+pysqlite:////tmp/live/pre.db; C="sqlite /tmp/live/pre.db"
fi
echo "### 1. base f5776828 backend on an empty $KIND DB ($URL): tables created by create_all; writes via its API"
echo "#    (temporary qualification override in the base worktree so the Pinned Run and run events can be created; reverted right after)"
cd $B && backend/.venv/bin/python /tmp/ui25_override.py >/dev/null
: > /tmp/live/backend-pre-base-$KIND.log
/tmp/live/with-stack.sh $B $URL /tmp/live/backend-pre-base-$KIND.log noweb -- /tmp/live/seed-old.sh
cd $B && git checkout -- skills/helix-evidence-pipeline/packages/sections && echo "base override reverted: $(git status --short skills | wc -l | tr -d ' ') changed files"
echo; echo "### 2. BEFORE (base schema, created without Alembic)"; /tmp/live/counts.sh $C | tee /tmp/live/pre-$KIND-before.txt
echo; echo "### 3. start the #19 backend (tip + env.py fix, no override) against the same DB"
: > /tmp/live/backend-pre-new-$KIND.log
/tmp/live/with-stack.sh $R $URL /tmp/live/backend-pre-new-$KIND.log noweb -- /tmp/live/check-new.sh
echo "--- #19 backend log:"; cat /tmp/live/backend-pre-new-$KIND.log
echo; echo "### 4. AFTER"; /tmp/live/counts.sh $C | tee /tmp/live/pre-$KIND-after.txt
echo; echo "### diff BEFORE -> AFTER"; diff /tmp/live/pre-$KIND-before.txt /tmp/live/pre-$KIND-after.txt
