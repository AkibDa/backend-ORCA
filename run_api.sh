#!/bin/bash
# run_api.sh
# This script sets environment variables to prevent PyTorch/XGBoost OpenMP segmentation faults
# in WSL before starting the FastAPI server.

export OMP_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE
export TF_ENABLE_ONEDNN_OPTS=0

source ~/orca-venv/bin/activate
cd /mnt/w/ORCA-team

echo "Starting FastAPI server..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
