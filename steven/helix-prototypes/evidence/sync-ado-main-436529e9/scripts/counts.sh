#!/bin/bash
# usage: counts.sh pg DB | counts.sh sqlite FILE
if [ "$1" = pg ]; then
  for t in $(/tmp/live/q 55441 $2 -Atc "select tablename from pg_tables where schemaname='public' order by 1"); do
    printf "%-24s %s\n" $t "$(/tmp/live/q 55441 $2 -Atc "select count(*) from $t")"; done
  echo "alembic_version: $(/tmp/live/q 55441 $2 -Atc "select version_num from alembic_version" 2>&1 | tr -d '\n')"
else
  for t in $(sqlite3 $2 "select name from sqlite_master where type='table' order by 1"); do printf "%-24s %s\n" $t "$(sqlite3 $2 "select count(*) from $t")"; done
  echo "alembic_version: $(sqlite3 $2 "select version_num from alembic_version" 2>&1)"
fi
