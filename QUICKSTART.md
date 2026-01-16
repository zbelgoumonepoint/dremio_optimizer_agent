# Quick Start Guide

## ⚠️ IMPORTANT: Always Activate UV Environment

Before running **ANY** command or script in this project, always activate the UV virtual environment:

```bash
cd /Users/z.belgoum/projects/dremio_optimizer_agent
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

## Quick Setup (First Time)

```bash
# 1. Navigate to project
cd /Users/z.belgoum/projects/dremio_optimizer_agent

# 2. Create UV environment (only once)
uv venv

# 3. Activate environment
source .venv/bin/activate

# 4. Install dependencies
uv pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary pydantic pydantic-settings requests python-dotenv langchain langgraph langchain-openai opentelemetry-api opentelemetry-sdk python-loki certifi

# 5. Configure .env file
cp .env.example .env
# Edit .env with your Dremio credentials

# 6. Setup database
python scripts/setup_db.py

# 7. Test connection
python test_connection.py
```

## Daily Usage

Every time you work on this project:

```bash
# 1. Activate environment
cd /Users/z.belgoum/projects/dremio_optimizer_agent
source .venv/bin/activate

# 2. Run your commands
python test_connection.py
python scripts/test_collection.py
```

## Convenient Alias (Recommended)

Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
alias dremio-env='cd /Users/z.belgoum/projects/dremio_optimizer_agent && source .venv/bin/activate'
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

Now you can just type:
```bash
dremio-env
```

And you'll be in the project directory with the environment activated!

## Common Commands

All commands require the UV environment to be activated first!

```bash
# Test Dremio connection
python test_connection.py

# Collect data from Dremio
python scripts/test_collection.py

# Setup/reset database
python scripts/setup_db.py

# Check if environment is activated
python -c "import sys; print(sys.prefix)"
# Should show: /Users/z.belgoum/projects/dremio_optimizer_agent/.venv
```

## Troubleshooting

### "Module not found" errors?
→ **Solution**: Make sure UV environment is activated (`source .venv/bin/activate`)

### How do I know if environment is activated?
→ **Check**: Your prompt should show `(.venv)` at the beginning

### Forgot to activate environment?
```bash
# Just activate it now
source .venv/bin/activate

# Or use the alias
dremio-env
```

## Project Structure

```
dremio_optimizer_agent/
├── .venv/              ← UV virtual environment (activate this!)
├── .env                ← Your configuration (Dremio credentials)
├── src/                ← Source code
├── scripts/            ← Setup and test scripts
├── documentation/      ← Detailed guides
├── test_connection.py  ← Quick connection test
└── QUICKSTART.md       ← This file
```

## Next Steps

After setup is complete, see:
- [SETUP_GUIDE.md](documentation/SETUP_GUIDE.md) - Detailed setup instructions
- [README.md](README.md) - Project overview
- [documentation/](documentation/) - All documentation

---

**Remember**: `source .venv/bin/activate` before every session! 🚀
