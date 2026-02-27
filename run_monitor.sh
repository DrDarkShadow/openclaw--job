#!/bin/bash
# OpenClaw Cron Job for Job Monitor
# Logs to /tmp/monitor.log

cd /home/ubuntu/.openclaw/workspace/jobs
/home/ubuntu/.openclaw/workspace/venv/bin/python3 live_monitor.py >> /tmp/monitor.log 2>&1
