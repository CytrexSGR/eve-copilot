#!/bin/bash
# WH Commodity Price Snapshotter - runs daily at 06:00 UTC
cd /home/cytrex/eve_copilot
/usr/bin/python3 jobs/wh_commodity_price_snapshotter.py >> logs/wh_commodity_snapshotter.log 2>&1
