#!/usr/bin/env python3
"""Quick test for Telegram integration"""

import asyncio
from src.telegram_service import telegram_service

async def main():
    print("Testing Telegram integration...")
    print()

    # Test alerts channel
    print("1. Testing ALERTS channel...")
    alert_msg = """🧪 **Test Alert**

This is a test message for the alerts channel!

If you see this, the bot is working correctly.
"""
    success = await telegram_service.send_alert(alert_msg)
    if success:
        print("   ✅ Alert sent successfully!")
    else:
        print("   ❌ Alert failed!")
        print("   Check:")
        print("   - Is bot admin in @infinimind_eve_alerts?")
        print("   - Does the channel exist?")

    print()

    # Test reports channel
    print("2. Testing REPORTS channel...")
    report_msg = """📊 **Test Report**

This is a test message for the reports channel!

If you see this, the bot is working correctly.
"""
    success = await telegram_service.send_report(report_msg)
    if success:
        print("   ✅ Report sent successfully!")
    else:
        print("   ❌ Report failed!")
        print("   Check:")
        print("   - Is bot admin in @infinimind_eve_reports?")
        print("   - Does the channel exist?")

    print()
    print("Done! Check your Telegram channels.")

if __name__ == "__main__":
    asyncio.run(main())
