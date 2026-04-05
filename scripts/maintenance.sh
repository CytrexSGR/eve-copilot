#!/bin/bash
# EVE Intelligence - Maintenance & Capacity Control
# Usage: ./maintenance.sh [on|off|status]

MAINTENANCE_FILE="/var/www/html/.maintenance"

case "$1" in
    on)
        sudo touch "$MAINTENANCE_FILE"
        echo "✅ Maintenance mode ENABLED"
        echo "   Site now shows maintenance page (503)"
        echo "   Run './maintenance.sh off' to disable"
        ;;
    off)
        sudo rm -f "$MAINTENANCE_FILE"
        echo "✅ Maintenance mode DISABLED"
        echo "   Site is back online"
        ;;
    status)
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  EVE Intelligence - System Status"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        # Maintenance status
        if [ -f "$MAINTENANCE_FILE" ]; then
            echo "🔧 Maintenance Mode: ON (503 → maintenance.html)"
        else
            echo "🟢 Maintenance Mode: OFF"
        fi
        echo ""
        # Waiting Room status (always active via nginx)
        echo "⏳ Waiting Room: ACTIVE"
        echo "   - Max 10 connections per IP"
        echo "   - Max 150 total connections"
        echo "   - Overflow → 429 → waiting-room.html"
        echo ""
        # Current connections
        CONNS=$(ss -s | grep "estab" | head -1 | awk '{print $4}' | tr -d ',')
        echo "📊 Current TCP connections: $CONNS"
        echo ""
        ;;
    *)
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  EVE Intelligence - Capacity Control"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Usage: $0 [on|off|status]"
        echo ""
        echo "  on     - Block ALL users (maintenance page)"
        echo "  off    - Allow users (waiting room still active)"
        echo "  status - Show system status"
        echo ""
        echo "Modes:"
        echo "  🔧 Maintenance (manual)  → 503 → maintenance.html"
        echo "  ⏳ Waiting Room (auto)   → 429 → waiting-room.html"
        echo ""
        ;;
esac
