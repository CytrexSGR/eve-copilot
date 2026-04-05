#!/usr/bin/env python3
"""Start zkillboard RedisQ listener for live kill streaming."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from services.zkillboard import zkill_live_service

if __name__ == "__main__":
    asyncio.run(zkill_live_service.listen_redisq(verbose=True))
