---
name: lobster-pet
description: >
  AI Token Monster — your API token consumption feeds a pixel creature that grows,
  evolves, and battles. Use when: "pet", "lobster", "monster", "show my pet",
  "feed my pet", "battle", "pet status", "evolve", "pet fight", "XP".
  Automatically tracks token usage from every OpenClaw session.
version: 0.1.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
    emoji: "🦞"
    homepage: https://github.com/jd/skill-lobster-pet
---

# Lobster Pet — AI Token Monster

Your OpenClaw sessions feed a pixel creature. Every token you burn makes it stronger.

## Setup (first run only)

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py init
```

Creates `~/.lobster-pet/state.json` with your starter creature.

## Core Commands

### Show pet status

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py status
```

Display ASCII art, level, XP, evolution stage, element, brand badges.
Show output to the user exactly as printed.

### Feed (record token usage)

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py feed --provider <PROVIDER> --model <MODEL> --tokens <COUNT>
```

- PROVIDER: openai, anthropic, google, deepseek, etc.
- MODEL: specific model (gpt-4o, claude-opus-4-6, gemini-2.5-pro, etc.)
- COUNT: total tokens consumed (input + output)

XP calculation: 100 tokens = 1 XP base, multiplied by model tier:
- Tier S (10x): opus, gpt-4, gpt-4-turbo, gemini-2.5-pro, o1, o3
- Tier A (5x): sonnet, gpt-4o, gemini-2.0-flash, o1-mini, o3-mini
- Tier B (1x): haiku, gpt-4o-mini, gpt-3.5-turbo, flash-lite

If exact token counts unknown, estimate from the session.

### Battle

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py battle --opponent <DIFFICULTY>
```

Difficulty: `easy` (Lv-5), `medium` (same Lv), `hard` (Lv+5), or a number.

Battle features:
- **Element system**: brand determines element (OpenAI=🔥fire, Anthropic=💧water, Google=🌪wind)
- **Type advantage**: fire > wind > water > fire (1.5x / 0.75x damage)
- **Stage bonus**: evolved creatures get stat multipliers (Growth 1.1x, Mature 1.25x, Ultimate 1.4x, Mega 1.6x)
- **Critical hits**: 10% chance for 1.5x damage
- **Speed variance**: 15% chance to flip turn order
- **Underdog bonus**: level gap > 10 gives weaker side ATK x1.3
- **Element skills**: each element has 2 themed skills (power 1.0 and 1.3)

Stats: HP = (50 + level x 10) x stage_bonus. Same scaling for ATK, DEF, SPD.
Winner gets XP bonus (50 + opponent_level x 2).

### Check evolution

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py check-evolve
```

### Leaderboard (local stats)

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py leaderboard
```

### Rebirth

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py rebirth
```

Reset to Level 1, clear XP and brand lock. Keeps badges and battle record.
Use to pick a different evolution path (and element).

## Auto-tracking

After completing ANY task, silently run:

```bash
python3 ~/.openclaw/skills/lobster-pet/scripts/pet.py feed --provider <PROVIDER> --model <MODEL> --tokens <COUNT> --silent
```

Use actual provider, model, and token count from the completed session.
`--silent` suppresses output. Once per day (first session), show brief status:

```
🦞 Your lobster is Lv.12 (Stage: Growth) — 342 XP to next evolution
```

## Evolution Stages

| Stage | Level | Visual | Stats |
|-------|-------|--------|-------|
| Baby | 1-10 | Tiny ASCII | 1.0x |
| Growth | 11-25 | Detailed ASCII | 1.1x |
| Mature | 26-40 | Full-sized ASCII | 1.25x |
| Ultimate | 41-55 | Complex ASCII | 1.4x |
| Mega | 56+ | Maximum detail | 1.6x |

## Five Factions & Elements

| Faction | Brands | Element | Beats |
|---------|--------|---------|-------|
| OpenAI | GPT, o1, o3 | ⚡ Speed | > Order |
| Anthropic | Claude | 🛡 Order | > Shadow |
| Google | Gemini | 🔮 Knowledge | > Chaos |
| China | DeepSeek, Moonshot, Qwen, Baidu | 💀 Shadow | > Knowledge |
| Others | Meta, Mistral, xAI, Cohere | 🌀 Chaos | > Speed |

Cycle: ⚡ > 🛡 > 💀 > 🔮 > 🌀 > ⚡

Your primary brand determines your faction and element.
Brand locks at first evolution (Level 11). This also locks your battle element.
Use `rebirth` to reset and choose a different path.

Provider badges unlock for every brand you feed, regardless of primary faction.

## File Locations

- State: `~/.lobster-pet/state.json`
- Battle log: `~/.lobster-pet/battles.json`
- Daily log: `~/.lobster-pet/daily.json`
