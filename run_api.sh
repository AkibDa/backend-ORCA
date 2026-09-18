#!/bin/bash

export OMP_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE
export TF_ENABLE_ONEDNN_OPTS=0

source /home/jeffcarter/orca-venv/bin/activate
cd /mnt/w/ORCA

echo "Starting FastAPI server..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000