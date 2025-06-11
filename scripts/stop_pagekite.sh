#!/bin/bash
# 🛑 Stop PageKite Tunnel

echo "🛑 Stopping PageKite tunnel..."

if [ -f "pagekite.pid" ]; then
    PID=$(cat pagekite.pid)
    kill $PID 2>/dev/null
    rm pagekite.pid
    echo "✅ PageKite tunnel stopped"
else
    # Fallback: kill any pagekite process
    pkill -f pagekite.py
    echo "✅ PageKite processes terminated"
fi 