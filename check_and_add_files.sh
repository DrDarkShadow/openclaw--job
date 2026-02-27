#!/bin/bash
# Script to check and add OpenClaw files to git repo
# This helps push configuration files while keeping secrets safe

echo "======================================"
echo "OpenClaw File Check & Add Script"
echo "======================================"

cd /home/ubuntu/.openclaw/workspace

echo ""
echo "📁 Checking files to add to repository..."

# Function to check and add file
check_and_add() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        echo "✅ Found: $file ($description)"
        cp "$file" "/home/ubuntu/.openclaw/workspace/jobs/repo_$(basename "$file")"
        return 0
    else
        echo "❌ Missing: $file"
        return 1
    fi
}

echo ""
echo "📋 Core OpenClaw Context Files:"

check_and_add "HEARTBEAT.md" "Job checking rules and automation"
check_and_add "AGENTS.md" "Workspace guidelines and protocols"
check_and_add "SOUL.md" "AI personality and behavior definition"
check_and_add "USER.md" "User information and preferences"
check_and_add "IDENTITY.md" "AI identity and avatar"
check_and_add "WORKFLOW_AUTO.md" "System workflows and automation"
check_and_add "TOOLS.md" "Local tools and environment configuration"

echo ""
echo "📋 Job System Documentation Files:"

check_and_add "jobs/README.md" "Job finder system documentation"
check_and_add "jobs/filtered_jobs_summary.md" "Example filtered job summaries"
check_and_add "jobs/fresh_jobs.md" "Example fresh job format"
check_and_add "jobs/get_cookies_instructions.md" "Authentication setup instructions"
check_and_add "jobs/job_notifications.md" "Notification examples and templates"

echo ""
echo "📋 Excluded Files (for privacy/security):"

# Check what we're NOT including
echo "❌ Excluded: memory/*.md (daily logs - private)"
echo "❌ Excluded: MEMORY.md (curated memory - private)"  
echo "❌ Excluded: resume.pdf (personal document)"
echo "❌ Excluded: cookies.json (authentication data)"
echo "❌ Excluded: email_config.json (email credentials)"
echo "❌ Excluded: *.db files (job tracking databases)"

echo ""
echo "======================================"
echo "📊 Summary:"
echo "Files copied to jobs/repo_* format"
echo "Run these commands to add to git:"
echo ""
echo "cd jobs/"
echo "git add repo_*.md"
echo "git commit -m 'docs: add OpenClaw context and documentation files'"
echo "git push origin main"
echo "======================================"