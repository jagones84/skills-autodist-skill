#!/usr/bin/env bash
# h3-doctor.sh - gate diagnostico (deve dire 0 FAIL, 0 WARN).
set -euo pipefail
exec bash /home/jagones/Repositories/diffusion-pipelines/film/h3/h3_doctor.sh "$@"
