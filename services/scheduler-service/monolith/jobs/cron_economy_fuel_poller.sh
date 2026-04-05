#!/bin/bash
cd /home/cytrex/eve_copilot
/usr/bin/python3 jobs/economy_fuel_poller.py >> logs/economy_fuel_poller.log 2>&1
