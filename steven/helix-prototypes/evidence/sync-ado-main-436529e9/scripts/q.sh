#!/bin/bash
port=$1; db=$2; shift 2; exec psql -h 127.0.0.1 -p $port -U helix -d $db "$@"
