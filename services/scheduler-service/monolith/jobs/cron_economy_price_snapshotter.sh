#!/bin/bash
# War Economy Price Snapshotter - runs every 30 minutes
cd /home/cytrex/eve_copilot
/usr/bin/python3 jobs/economy_price_snapshotter.py >> logs/economy_price_snapshotter.log 2>&1
