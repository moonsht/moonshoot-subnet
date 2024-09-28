#!/bin/bash

python3 -m venv venv_miner_dashboard
source venv_miner_dashboard/bin/activate
pip install -r requirements.txt

cp -r env venv_miner_dashboard/

export PYTHONPATH=$(pwd)
echo "PYTHONPATH is set to $PYTHONPATH"
NETWORK_TYPE=${1:-mainnet}
cd src
python3 subnet/miner_dashboard/main.py $NETWORK_TYPE

deactivate