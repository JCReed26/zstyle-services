#!/bin/bash
# OpenMemory Installation Fix Script
# This script fixes the incorrect openmemory package installation

set -e

echo "🔍 Checking current installation..."

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected. Activating .venv..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "❌ No .venv directory found. Please create a virtual environment first."
        exit 1
    fi
fi

echo "📦 Current packages:"
pip list | grep -E "openmemory|google-adk" || echo "  (none found)"

echo ""
echo "🗑️  Uninstalling incorrect openmemory package..."
pip uninstall openmemory -y || echo "  (package not found, continuing...)"

echo ""
echo "📥 Installing correct openmemory-py package..."
pip install "openmemory-py>=1.0.0,<2.0.0"

echo ""
echo "✅ Verifying installation..."
pip show openmemory-py

echo ""
echo "🧪 Testing imports..."
python3 -c "
try:
    from openmemory.client import Memory
    print('✅ OpenMemory import successful')
    
    from google.adk.agents import Agent
    print('✅ Google ADK Agent import successful')
    
    from google.adk.tools.agent_tool import AgentTool
    print('✅ Google ADK AgentTool import successful')
    
    from google.adk.memory import BaseMemoryService
    print('✅ Google ADK BaseMemoryService import successful')
    
    print('')
    print('🎉 All imports successful!')
except Exception as e:
    print(f'❌ Import failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo ""
echo "✨ Installation fix complete!"
