# ZStyle CLI - Chat with Agents

A simple CLI to chat with AI agents powered by Google's Gemini model.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
```bash
cp .env.example .env
# Edit .env and add your Google API key
export GOOGLE_API_KEY=your-key-here
```

Get your key: https://makersuite.google.com/app/apikey

## Usage

### Start Backend
```bash
uvicorn app.main:app --reload
```

### Run CLI (in another terminal)
```bash
python -m app.cli.main
```

### Examples

**Interactive menu:**
```bash
python -m app.cli.main
```

**Chat with specific agent:**
```bash
python -m app.cli.main --agent fitness_coach
python -m app.cli.main --agent personal_assistant
python -m app.cli.main --agent nutritionist
python -m app.cli.main --agent exec_func_coach
```

**Custom user ID:**
```bash
python -m app.cli.main --user-id alice
```

## Available Agents

1. **exec_func_coach** - Executive function and productivity
2. **fitness_coach** - Fitness and exercise guidance
3. **nutritionist** - Nutrition and diet advice
4. **personal_assistant** - General assistance and task management

## Commands

In the CLI:
- Type your message and hit Enter
- `back` - Return to agent menu
- `exit` or `quit` - Exit the program
