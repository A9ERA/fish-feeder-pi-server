#!/bin/bash
# 🚀 Start PageKite Tunnel for Fish Feeder

echo "🌐 Starting PageKite tunnel..."
echo "🔗 URL: https://b65iee02.pagekite.me"

# Start PageKite in background
pagekite.py 5000 b65iee02.pagekite.me &

# Save PID for stopping later
echo $! > pagekite.pid

echo "✅ PageKite tunnel started!"
echo "🌐 Access your Fish Feeder at: https://b65iee02.pagekite.me"
echo "🛑 To stop: ./stop_pagekite.sh" 