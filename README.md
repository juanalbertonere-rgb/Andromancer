# AndroMancer
![GitHub stars](https://img.shields.io/github/stars/juanalbertonere-rgb/andromancer?style=social)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)
![LLM](https://img.shields.io/badge/LLM-Groq%20|%20Llama%203.3-orange)

**An autonomous Android agent powered by AI reasoning and modular skills.**

AndroMancer is an intelligent automation framework that enables devices running Android to be controlled autonomously through natural language goals. It combines ReAct reasoning, specialized skills, and adaptive recovery mechanisms to accomplish complex multi-step tasks on Android devices.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (or Termux on Android)
- **ADB** (Android Debug Bridge) installed and configured
- **Android device** with wireless debugging enabled and USB Debugging
- **GROQ API Key** (or alternative LLM provider)
- **Node.js 14+** (for web dashboard)

### Installation

1. **Clone or extract the repository:**
   ```bash
   git clone <repository-url>
   cd andromancer
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   # or in Termux:
   pip install --break-system-packages -r requirements.txt
   ```

3. **Install Node dependencies (optional, for web dashboard):**
   ```bash
   cd server_node
   npm install
   cd ..
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   GROQ_API_KEY=your_actual_api_key_here
   MODEL_NAME=llama-3.3-70b-versatile
   MAX_STEPS=20
   ADB_TIMEOUT=15
   LOG_LEVEL=INFO
   AUTONOMY_LEVEL=full
   CONFIDENCE_THRESHOLD=0.75
   PARALLEL_ACTIONS=True
   ```

5. **Ensure ADB is connected:**
   ```bash
   adb devices
   ```
   You should see your device listed.

---

## 📖 Usage

### Method 1: Command Line Interface (CLI)

Run AndroMancer with a goal:

```bash
python -m andromancer "open whatsapp and send hello to john"
```

Interactive mode:
```bash
python -m andromancer
# Then type commands like:
# > mission open chrome
# > status
# > memory
# > help
```

### Method 2: Web Dashboard

Start the Node.js server:

```bash
cd server_node
node server.js
```

Open your browser to `http://localhost:3000` and send commands through the web interface.

### Method 3: Telegram Bot

Set your Telegram token in `.env` or `settings.py`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Start the server:
```bash
cd server_node
node server.js
```

Send commands to your Telegram bot prefixed with `do`:
```
do open settings and enable wifi
do take a screenshot
```

---

## 🏗️ Architecture

### Core Components

```
andromancer/
├── core/
│   ├── agent.py          # Main autonomous agent loop
│   ├── reasoning.py      # ReAct engine with LLM integration
│   ├── llm_client.py     # GROQ/OpenAI API client
│   ├── memory.py         # Semantic memory with hash embeddings
│   ├── capabilities/     # Low-level device actions
│   │   ├── interaction.py     (tap, type, swipe, back)
│   │   ├── navigation.py      (open_app, home)
│   │   └── observation.py     (UI scraping, screen analysis)
│   └── __init__.py
├── skills/
│   ├── base.py                    # Skill interface & registry
│   ├── critical/                  # CRITICAL priority (override LLM)
│   │   ├── app_opener.py         (Open apps by pattern matching)
│   │   └── __init__.py
│   ├── advisory/                  # ADVISORY priority (suggest to LLM)
│   │   ├── settings_escape.py    (Warn if stuck in settings)
│   │   └── __init__.py
│   └── emergency/                 # EMERGENCY recovery skills
│       ├── pattern.py            (Detect & break loops)
│       ├── home_rescue.py        (Reset to home screen)
│       └── __init__.py
├── utils/
│   ├── adb.py                    # ADB manager & device control
│   └── __init__.py
├── cli.py                         # Command-line interface
├── config.py                      # Settings loader
└── __main__.py                    # Entry point

server_node/
├── server.js                      # Express + Socket.io + Telegram
├── public/
│   └── index.html                 # Web dashboard UI
├── package.json
└── package-lock.json
```

### Execution Flow

```
User Goal
    ↓
[OBSERVATION] Get current UI state
    ↓
[SKILL CHECK] Are any specialized skills applicable?
    ├─ YES → Execute skill plan + REFLECT
    └─ NO ↓
[REASONING] LLM analyzes state & generates action plan
    ↓
[ACTION] Execute capabilities in parallel or sequence
    ↓
[REFLECTION] Learn from success/failure
    ↓
[LOOP] Repeat until goal achieved or max steps reached
```

---

## 🎯 Key Features

### 1. **ReAct Reasoning Engine**
- Combines Reasoning + Acting for autonomous decision-making
- Integrates with GROQ/OpenAI LLMs
- Maintains thought history and working memory
- Learns from previous experiences

### 2. **Modular Skill System**
Three priority levels:
- **CRITICAL**: Overrides LLM (e.g., "open WhatsApp" → use AppOpenSkill)
- **ADVISORY**: Suggests alternatives to LLM (e.g., "you're in Settings, exit?")
- **EMERGENCY**: Recovery skills (detect loops, reset to home)

### 3. **Semantic Memory**
- Hash-based vector embeddings (simple, no external DB needed)
- Retrieves relevant past experiences
- Improves decision-making in similar situations

### 4. **Parallel Action Execution**
- Execute independent actions simultaneously (when safe)
- Respects dependency graphs
- Configurable via `PARALLEL_ACTIONS` env var

### 5. **Event Bus Architecture**
- Decoupled event system for logging & monitoring
- Supports external handlers/webhooks
- Full mission lifecycle tracking

### 6. **Safety Checkpoints**
- High-risk actions require approval
- Confidence thresholds for autonomous execution
- Respects `AUTONOMY_LEVEL` setting

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Your GROQ API key |
| `MODEL_NAME` | `llama-3.3-70b-versatile` | LLM model to use |
| `MAX_STEPS` | 20 | Maximum action steps per mission |
| `ADB_TIMEOUT` | 15 | ADB command timeout (seconds) |
| `ADB_DELAY` | 1.0 | Delay between ADB commands |
| `AUTONOMY_LEVEL` | `full` | `full` / `assisted` / `manual` |
| `CONFIDENCE_THRESHOLD` | 0.75 | Min confidence for autonomous action |
| `PARALLEL_ACTIONS` | `True` | Enable parallel execution |
| `SAFETY_CHECKPOINTS` | `True` | Require approval for risky actions |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `TELEGRAM_BOT_TOKEN` | (optional) | Telegram bot token |
| `TELEGRAM_CHAT_ID` | (optional) | Telegram chat ID for notifications |

### settings.py

Alternative to `.env` for advanced users:

```python
# settings.py
GROQ_API_KEY = "sk-..."
MODEL_NAME = "llama-3.3-70b-versatile"
MAX_STEPS = 20
AUTONOMY_LEVEL = "full"
CONFIDENCE_THRESHOLD = 0.75
PARALLEL_ACTIONS = True
SAFETY_CHECKPOINTS = True
```

---

## 💡 Usage Examples

### Example 1: Open an App
```bash
python -m andromancer "open whatsapp"
```
**What happens:**
1. AppOpenerSkill detects the intent
2. Skill overrides LLM with high confidence (0.95)
3. `open_app` capability executes
4. Device opens WhatsApp

### Example 2: Multi-Step Task
```bash
python -m andromancer "open settings and enable wifi"
```
**What happens:**
1. Open Settings (via AppOpenerSkill)
2. Observe UI → find WiFi toggle
3. LLM generates tap action
4. Execute tap → WiFi enabled

### Example 3: Interactive Session
```bash
python -m andromancer

# CLI prompt appears:
🤖 Agent> mission send a message to alice
📍 Step 1/20 → (agent thinks and acts)
✅ Mission completed in 5 steps
```

### Example 4: Web Dashboard
```bash
cd server_node
node server.js
# Open http://localhost:3000
# Type: "open chrome and search for python tutorials"
```

---

## 🔧 Advanced Topics

### Writing Custom Skills

Create a new skill in `andromancer/skills/custom/`:

```python
# andromancer/skills/custom/my_skill.py
from andromancer.skills.base import Skill, SkillResult, SkillPriority

class MyCustomSkill(Skill):
    name = "MySkill"
    priority = SkillPriority.ADVISORY  # or CRITICAL, EMERGENCY
    
    async def evaluate(self, goal: str, observation: dict, history: list) -> SkillResult:
        # Check if this skill applies
        if "my_pattern" in goal.lower():
            return SkillResult(
                can_handle=True,
                confidence=0.85,
                actions=[
                    {"capability": "tap", "params": {"x": 100, "y": 200}},
                    {"capability": "type", "params": {"text": "hello"}}
                ],
                override_llm=True,
                suggestion="Executing custom skill..."
            )
        
        return SkillResult(can_handle=False, confidence=0.0, actions=[])
```

Register it in `andromancer/core/agent.py`:
```python
def _register_default_skills(self):
    # ... existing skills ...
    self.skill_registry.register(MyCustomSkill())
```

### Extending Capabilities

Add new low-level actions in `andromancer/core/capabilities/`:

```python
# andromancer/core/capabilities/custom.py
from andromancer.core.capabilities.base import ADBCapability, Capability, ExecutionResult

class LongPressCapability(ADBCapability, Capability):
    name = "long_press"
    description = "Long press at coordinates"
    risk_level = "medium"
    
    async def execute(self, x: int, y: int, duration: int = 1000) -> ExecutionResult:
        result = await self._adb([
            "shell", "input", "swipe", 
            str(x), str(y), str(x), str(y), str(duration)
        ])
        success = result.returncode == 0
        return ExecutionResult(success, data={"x": x, "y": y, "duration": duration})
```

### Custom LLM Provider

Replace GROQ with another provider:

```python
# In your code
from andromancer.core.reasoning import ReActEngine
from andromancer.core.llm_client import AsyncLLMClient

class CustomLLMClient(AsyncLLMClient):
    async def complete_chat(self, system_prompt: str, user_prompt: str) -> dict:
        # Your custom API call here
        pass

engine = ReActEngine(llm_client=CustomLLMClient())
```

---

## 📊 Monitoring & Debugging

### View Logs

```bash
# Real-time logs
tail -f ~/.andromancer/agent.log

# Or through CLI
python -m andromancer
> memory  # View stored memories
> status  # Check current mission
```

### Enable Debug Mode

```bash
export ANDROMANCER_DEBUG_PRINT=True
export LOG_LEVEL=DEBUG
python -m andromancer "your goal"
```

### Event Monitoring

Hook into the event bus:

```python
from andromancer.core.agent import event_bus, EventType

async def my_event_handler(event):
    if event.type == EventType.ACTION:
        print(f"Action: {event.content}")

event_bus.subscribe(my_event_handler)
```

---

## 🛠️ Troubleshooting

### ADB Connection Issues

```bash
# Check if ADB sees your device
adb devices

# If not listed, restart ADB:
adb kill-server
adb start-server
adb devices

# Enable USB debugging on your Android device:
# Settings → Developer Options → USB Debugging → ON
```

### LLM API Errors

```bash
# Test your API key
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"test"}]}'
```

### App Not Opening

The `AppOpenerSkill` attempts multiple strategies:
1. Check app map (WhatsApp → com.whatsapp)
2. Query ADB for installed packages
3. Fall back to LLM reasoning

For unsupported apps:
```python
# In andromancer/skills/critical/app_opener.py
app_map = {
    "myapp": "com.example.myapp",  # Add here
    # ...
}
```

### Memory Issues

Clear memory cache:
```bash
rm ~/.andromancer/memory.vec
```

Reset mission state:
```bash
rm ~/.andromancer/agent_state.json
```

---

## 📦 Requirements

See `requirements.txt`:

```
groq>=0.9.0
requests>=2.28.0
pillow>=9.0.0
pytesseract>=0.3.10
```

For Node.js web dashboard:
- express ^5.2.1
- socket.io ^4.8.3
- telegraf ^4.16.3
- axios ^1.13.4

---

## 📜 License

This project is licensed under the **Apache License 2.0**. See `LICENSE` file for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add my feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## ⚠️ Disclaimer

AndroMancer is designed for automation of your own Android devices. **Use responsibly and ethically.** The authors assume no liability for misuse.

- Only control devices you own or have explicit permission to control
- Respect privacy and security
- Test in non-production environments first

---

## 🎓 Learning Resources

### ReAct Pattern
- Paper: [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- Combines explicit reasoning chains with agent actions for improved performance

### Android Automation
- [Android Debug Bridge (ADB) Documentation](https://developer.android.com/tools/adb)
- [UIAutomator Documentation](https://developer.android.com/tools/testing-samples/ui-automator)

### GROQ API
- [GROQ Console](https://console.groq.com)
- Models: llama-3.3-70b, mixtral-8x7b-32768, and more

---

## 📞 Support

- **Issues:** Open an issue on GitHub with details of your problem
- **Discussions:** Use GitHub Discussions for questions and ideas
- **Email:** Contact the maintainers directly

---

## 🚀 Roadmap

- [ ] Web UI improvements (drag-drop workflow builder)
- [ ] Multi-device support (control multiple Android devices)
- [ ] Vision-based action detection (CV for visual confirmation)
- [ ] Custom action recording (teach by example)
- [ ] Persistent skill marketplace
- [ ] Better memory compression (reduce file size)
- [ ] Rate limiting & quota management for API calls

---

**Made with ❤️ by the AndroMancer Team**

*AndroMancer — Autonomous Android Intelligence*


