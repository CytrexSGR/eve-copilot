#!/bin/bash
# Quick Dev Server for fast frontend development
# Hot reload enabled - changes appear instantly!
# ALWAYS on port 5175 - kills any existing dev server first

DEV_PORT=5175

# Kill any existing vite dev processes (not Docker/nginx on 5173)
existing=$(lsof -ti :$DEV_PORT 2>/dev/null)
if [ -n "$existing" ]; then
  echo "Killing existing process on port $DEV_PORT (PID: $existing)"
  kill $existing 2>/dev/null
  sleep 1
fi

echo "Starting Frontend Dev Server with Hot Reload..."
echo "URL: http://localhost:$DEV_PORT"
echo "Changes auto-reload in ~200ms"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev -- --port $DEV_PORT --strictPort --host 0.0.0.0
