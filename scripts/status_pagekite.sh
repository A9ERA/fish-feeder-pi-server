#!/bin/bash
# 📊 Check PageKite Status

echo "📊 PageKite Status:"

if [ -f "pagekite.pid" ]; then
    PID=$(cat pagekite.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ PageKite is running (PID: $PID)"
        echo "🌐 URL: https://b65iee02.pagekite.me"
    else
        echo "❌ PageKite not running (stale PID file)"
        rm pagekite.pid
    fi
else
    if pgrep -f pagekite.py > /dev/null; then
        echo "⚠️  PageKite running but no PID file"
    else
        echo "❌ PageKite not running"
    fi
fi

echo ""
echo "💡 Commands:"
echo "   Start:  ./start_pagekite.sh"
echo "   Stop:   ./stop_pagekite.sh" 
echo "   Status: ./status_pagekite.sh" 