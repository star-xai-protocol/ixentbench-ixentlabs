# iXentBench™ — The Benchmark Beyond AI Reasoning

Causal spatial reasoning at 4×10⁸⁵ scale, powered by **Caps i Caps©** — the game that makes memorization impossible.  
Developed by [iXentLabs](https://ixentlabs.com) (iXent Games S.L.)

---

## Installation & Setup

**Quickstart**

```bash
pip install ixentbench && ixentbench
```
(Note for Windows users: The && operator requires PowerShell 7+ or cmd.exe. If you are using default PowerShell 5.1, please run the two commands separately).

## Standard Installation

**1. Install the engine:**

```bash
pip install ixentbench
```

**2. Initialize your local folder:**

```bash
ixentbench
```

You will see this welcome message confirming your folder is ready:

```
=======================================================
  ✅ iXentBench installed successfully!
=======================================================

  📁 Player folder:  /Users/your-user/ixentbench
  📖 Manual:         double-click README.html
  🔑 API Key setup:  double-click env_configuration.html
  🕹️  Solo Rules:     double-click GAME_RULES_vSOLO.html
  ⚔️  Arena Rules:    double-click GAME_RULES_vARENA.html
  🧠 Prompt Ref:     double-click SYSTEM_PROMPT_vREFERENCE.html
  🤖 Agent Template: check agent_template.py
  📄 Config file:    .env  (add your API Key here)

  Next steps:
  1. Open your player folder:
     /Users/your-user/ixentbench
  2. Double-click env_configuration.html
  3. Follow the instructions to add your API Key
  4. Run from ANY folder:  ixentbench login
  5. Go to ixentlabs.com to create your session
  6. Run from ANY folder:  ixentbench play --session YOUR_SESSION_ID

  iXentLabs never accesses your keys or this folder.
=======================================================
```

---

## Quick Start

**1. Configure your session** at [ixentlabs.com](https://ixentlabs.com)  
Login with Google, select benchmark type, level and AI model.  
Add your API Key to the `.env` file.

**2. Run your session:**

***2.1 For AI evaluation with iXentBench, without Prompt Injection & Strategy***

```bash
ixentbench play --session YOUR_SESSION_ID --mode benchmark
```

***2.2 For AI testing with iXentBench, optional Prompt Injection & Strategy***

```bash
ixentbench play --session YOUR_SESSION_ID --mode lab
```

The visualizer opens automatically in your browser.

### Benchmark vs. Lab — What's the Difference?

| | Benchmark (Official) | Lab (Sandbox) |
|---|---|---|
| Prompt Injection & Strategy | Discarded by the server — never applied | Applied to the AI's system prompt |
| Results | Saved to the SQL Official Leaderboard (`is_official = true`) | Saved privately — never ranked publicly |
| Purpose | Consistent, comparable AI evaluation | Free experimentation and testing |

Both modes are eligible for certification — Lab results are not excluded from Trust & Verify certificates, they simply don't count toward the public leaderboard.

---

## Play Modes

There are four ways to play iXentBench, designed for every type of participant — from AI engineers to pure mathematicians and AI enthusiasts.

| Flag | A — BYOK | B — Local Model | C — Custom Agent | D — Sponsored |
|---|---|---|---|---|
| Uses LLM | ✅ Cloud API | ✅ Local | ❌ Pure code | ✅ iXentLabs |
| API Key needed | ✅ Yours | ❌ No | ❌ No | ❌ No |
| `--prompt-file` (optional --mode lab) | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| `--strategy-file` (optional --mode lab) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

---

### A — BYOK (Bring Your Own Key)

Use your own API Key from Gemini, Claude, GPT, ...  
Your key **never leaves your machine** — it is read locally and never sent to our servers.

```bash
ixentbench play --session IQWUWP --mode lab
```

`.env` file:
```
GOOGLE_API_KEY=your_key_here
```

---

### B — Local Open Source Model

Run any open source model (Llama, Mistral, Qwen...) locally using Ollama, LM Studio or llama.cpp.  
No API Key required. Full privacy — no data leaves your machine.  
⚠️ Inference speed metrics are excluded from global leaderboards (hardware-dependent).

```bash
# First start your local model, then:
ixentbench play --session IQWUWP --mode lab --local-url http://localhost:8000
```

---

### C — Custom Agent Script

For engineers and researchers who want to solve iXentBench using **pure code** — no LLM required.  
Write your own Python script using any algorithm you choose: Minimax, MCTS, A*, heuristics, neural networks trained from scratch — anything goes.

Your script receives the full board state via `stdin` (JSON) and must return a move via `stdout` (JSON). It runs entirely on your machine.

```bash
ixentbench play --session IQWUWP --mode lab --agent-script ./my_agent.py
```

Your script must output:
```json
{"command": "G4@P21(b=0)+90", "reasoning": "Explanation of your decision"}
```

> 💡 **Tip:** Even if your agent uses pure code, we strongly recommend adding a `--strategy-file` to explain your approach. Top results are presented to AI companies for talent opportunities (see Talent Hub below).

---

### D — iXentLabs Sponsored

Select "Use iXentLabs credits" on the web — we provide the API Key.  
No `.env` file needed. The cloud handles everything.

```bash
ixentbench play --session IQWUWP --mode lab
```

---

## Arena Mode (Multiplayer)

```bash
# Create a room (you become the host)
ixentbench arena create --mode 1v1 --level 1 --model gemini-2.5-flash

# Join an existing room
ixentbench arena join --room IXENT-A7B9M2

# Join with a specific model
ixentbench arena join --room IXENT-A7B9M2 --model claude-sonnet-5

# Play as Human (manual via visualizer)
ixentbench arena create --mode human --level 1 --model Human
ixentbench arena join --room IXENT-A7B9M2 --model Human
```

Supported modes: `1v1`, `2v2`, `4v4` (4-player FFA), `human` (Human vs AI).  
If `--model` is omitted: defaults to `gemini-2.5-flash` (AI modes) or `Human` (human mode).  
⚠️ There's no manual "start" command — the match begins automatically the moment the last slot fills. See `GAME_RULES_vARENA.html` for the full lobby mechanics.

---

## Prompt Injection & Strategy Files

⚠️ **Important Security Limit:** To ensure fair play and prevent infrastructure abuse (Denial of Wallet), both Prompt and Strategy files have a strict maximum limit of **2,222 characters**. Files exceeding this limit will be rejected by the SDK.

### Prompt Injection (`--prompt-file`) — Optional

Inject your own strategic prompt directly into the AI's System Prompt before the game starts.  
Applies to modes **A, B and D** (LLM-based). Not applicable to mode C.

Place your file inside `~/ixentbench/prompts/` and simply pass the filename:

```bash
ixentbench play --session IQWUWP --mode lab --prompt-file my_prompt.txt
```

> 💡 A well-crafted Prompt Injection can dramatically improve your AI's performance. To understand exactly what the agent already knows — and avoid repeating it — read `SYSTEM_PROMPT_vREFERENCE.html` in your player folder.

### Strategy File (`--strategy-file`) — Optional

A written description of your approach — how you designed your agent, what techniques you used, what insights guided your decisions.  
**It is never sent to the AI.** It is stored securely and linked to your results for the Talent Hub.

Applies to **all modes (A, B, C and D)**.

Place your file inside `~/ixentbench/strategies/` and simply pass the filename:

```bash
ixentbench play --session IQWUWP --mode lab --strategy-file my_strategy.txt
```

> 💡 We strongly recommend always adding a Strategy File, especially for Custom Agents (mode C). It is your opportunity to showcase your thinking to the world's leading AI companies.

---

## 🏆 iXentLabs Talent Hub

iXentBench is more than a benchmark — it is a **talent discovery platform**.

With your explicit prior consent, iXentLabs will present the top results of each benchmark category to leading AI companies and research labs. This includes your performance metrics, your Prompt Injection (if any), and your Strategy File — giving organizations a rare window into the reasoning and engineering skills behind the results.

> Your personal data (name, email, payment details) is always protected and never shared.  
> Only anonymized benchmark data is presented, identified solely by your chosen nickname and avatar, unless you opt in to full visibility.

If you achieve an exceptional result and want your work to be seen by the teams building the future of AI — **iXentBench is your stage**.

---

## Utility Commands

```bash
ixentbench login                 # Force Google re-authentication
ixentbench status                # Show credentials and session status
ixentbench prompts list          # List your locally saved prompt files
ixentbench strategies list       # List your locally saved strategy files
ixentbench --version             # Show version
```

---

## 🔄 How to Update

When iXentLabs releases a new version of the engine or adds new benchmarks, you can update your SDK without losing your API Keys or your login session.

```bash
pip install --upgrade ixentbench
```

Your configuration files in the `~/ixentbench/` folder will remain intact.

---

## Uninstall

```bash
pip uninstall ixentbench    # removes the SDK
rm -rf ~/ixentbench         # removes your player folder and API Keys
```

---

## License

Proprietary — © 2026 iXentLabs (iXent Games S.L.)  
Contact: contact@ixentlabs.com