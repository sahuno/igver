#!/bin/bash

# IGVer Agent Setup Script
# This script sets up a Python virtual environment and installs all dependencies

set -e  # Exit on error

echo "================================================"
echo "🧬 IGVer Genomic AI Agent Setup"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Check Python version
echo -e "\n${YELLOW}Step 1: Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then 
    echo -e "${GREEN}✅ Python $PYTHON_VERSION is compatible${NC}"
else
    echo -e "${RED}❌ Python $PYTHON_VERSION is too old. Requires Python 3.8+${NC}"
    exit 1
fi

# Step 2: Create virtual environment
echo -e "\n${YELLOW}Step 2: Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

python3 -m venv venv
echo -e "${GREEN}✅ Virtual environment created${NC}"

# Step 3: Activate virtual environment
echo -e "\n${YELLOW}Step 3: Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Step 4: Upgrade pip
echo -e "\n${YELLOW}Step 4: Upgrading pip...${NC}"
pip install --upgrade pip wheel setuptools --quiet
echo -e "${GREEN}✅ Pip upgraded${NC}"

# Step 5: Install dependencies
echo -e "\n${YELLOW}Step 5: Installing dependencies...${NC}"
echo "This may take a few minutes..."

# Install core dependencies first
pip install Pillow matplotlib requests --quiet
echo "  ✓ Core dependencies installed"

# Install IGVer (parent package)
pip install -e .. --quiet
echo "  ✓ IGVer package installed"

# Install AI providers (optional, but try both)
echo -e "\n${YELLOW}Installing AI providers (optional)...${NC}"

# Try installing OpenAI
if pip install openai --quiet 2>/dev/null; then
    echo -e "  ${GREEN}✓ OpenAI package installed${NC}"
else
    echo -e "  ${YELLOW}⚠ OpenAI package installation failed (optional)${NC}"
fi

# Try installing Anthropic
if pip install anthropic --quiet 2>/dev/null; then
    echo -e "  ${GREEN}✓ Anthropic package installed${NC}"
else
    echo -e "  ${YELLOW}⚠ Anthropic package installation failed (optional)${NC}"
fi

# Install optional dependencies
echo -e "\n${YELLOW}Installing optional dependencies...${NC}"
pip install python-dotenv tqdm colorama tabulate --quiet
echo -e "${GREEN}✅ Optional dependencies installed${NC}"

# Step 6: Create .env template if it doesn't exist
echo -e "\n${YELLOW}Step 6: Setting up configuration...${NC}"
if [ ! -f ".env" ]; then
    cat > .env.template << EOF
# IGVer Agent Environment Variables
# Copy this file to .env and fill in your API keys

# OpenAI API Key (for GPT-4V analysis)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key (for Claude vision analysis)  
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# IGVer Settings
IGVER_IMAGE=docker://sahuno/igver:latest
TMPDIR=/tmp
EOF
    echo -e "${GREEN}✅ Created .env.template - Copy to .env and add your API keys${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Step 7: Verify installation
echo -e "\n${YELLOW}Step 7: Verifying installation...${NC}"
python -c "
import sys
try:
    import igver
    print('  ✓ IGVer package: OK')
except ImportError as e:
    print(f'  ✗ IGVer package: FAILED - {e}')
    sys.exit(1)

try:
    from main_igver_agent_fixed import GenomicAIAgent
    print('  ✓ Agent module: OK')
except ImportError as e:
    print(f'  ✗ Agent module: FAILED - {e}')
    sys.exit(1)

try:
    import openai
    print(f'  ✓ OpenAI: {openai.__version__ if hasattr(openai, \"__version__\") else \"v0.x\"}')
except ImportError:
    print('  ⚠ OpenAI: Not installed (optional)')

try:
    import anthropic
    print(f'  ✓ Anthropic: {anthropic.__version__ if hasattr(anthropic, \"__version__\") else \"installed\"}')
except ImportError:
    print('  ⚠ Anthropic: Not installed (optional)')

# Check for API keys
import os
if os.environ.get('OPENAI_API_KEY'):
    print('  ✓ OpenAI API key: Found in environment')
elif os.path.exists('.env'):
    print('  ⚠ OpenAI API key: Check .env file')
else:
    print('  ⚠ OpenAI API key: Not configured')
"

# Step 8: Create run script
echo -e "\n${YELLOW}Step 8: Creating run script...${NC}"
cat > run_agent.sh << 'EOF'
#!/bin/bash
# Convenience script to run the agent with virtual environment

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the agent
python main_igver_agent_fixed.py "$@"
EOF

chmod +x run_agent.sh
echo -e "${GREEN}✅ Created run_agent.sh script${NC}"

# Final message
echo -e "\n================================================"
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo -e "================================================"
echo ""
echo "To use the agent:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Configure API keys: cp .env.template .env && nano .env"
echo "  3. Run agent: ./run_agent.sh"
echo ""
echo "Or use Python directly:"
echo "  python main_igver_agent_fixed.py"
echo ""
echo "To test with mock AI (no API key needed):"
echo "  python test_agent_logic_only.py"
echo ""