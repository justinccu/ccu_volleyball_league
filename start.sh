#!/bin/bash
conda init
conda activate flask-env
pip install -r requirements.txt
python init_data.py
python run.py