#!/usr/bin/env python3
"""
Lobster Pet — AI Token Monster
Your OpenClaw sessions feed a pixel creature that grows, evolves, and battles.
"""

import json
import os
import sys
import random
from datetime import datetime, date
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────

PET_DIR = Path.home() / ".lobster-pet"
STATE_FILE = PET_DIR / "state.json"
BATTLES_FILE = PET_DIR / "battles.json"
DAILY_FILE = PET_DIR / "daily.json"

# XP: 100 tokens = 1 XP base, multiplied by model tier
MODEL_TIERS = {
    # Tier S (10x): flagship / reasoning models
    "claude-opus-4-6": 10, "claude-opus-4-5-20250620": 10,
    "gpt-4": 10, "gpt-4-turbo": 10, "gpt-4-0125-preview": 10,
    "gemini-2.5-pro": 10, "o1": 10, "o1-pro": 10, "o3": 10,
    # Tier A (5x): strong general models
    "claude-sonnet-4-6": 5, "claude-sonnet-4-5-20241022": 5,
    "gpt-4o": 5, "gpt-4o-2024-11-20": 5,
    "gemini-2.0-flash": 5, "o1-mini": 5, "o3-mini": 5,
    # Tier B: 1x (default)
    "claude-haiku-4-5-20251001": 1,
    "gpt-4o-mini": 1, "gpt-3.5-turbo": 1,
    "gemini-2.0-flash-lite": 1,
}

EVOLUTION_STAGES = [
    {"name": "Baby",     "min_level": 1,  "max_level": 10},
    {"name": "Growth",   "min_level": 11, "max_level": 25},
    {"name": "Mature",   "min_level": 26, "max_level": 40},
    {"name": "Ultimate", "min_level": 41, "max_level": 55},
    {"name": "Mega",     "min_level": 56, "max_level": 999},
]

BRAND_COLORS = {
    "openai":    ("red",    "🔴"),
    "anthropic": ("blue",   "🔵"),
    "google":    ("green",  "🟢"),
    "deepseek":  ("purple", "🟣"),
    "moonshot":  ("purple", "🟣"),
    "qwen":      ("purple", "🟣"),
    "baidu":     ("purple", "🟣"),
    "meta":      ("orange", "🟠"),
    "mistral":   ("orange", "🟠"),
    "xai":       ("orange", "🟠"),
    "cohere":    ("orange", "🟠"),
    "other":     ("orange", "🟠"),
}

# Brand → Faction (for grouping)
BRAND_FACTION = {
    "openai":    "openai",
    "anthropic": "anthropic",
    "google":    "google",
    # Chinese faction
    "deepseek":  "china",
    "moonshot":  "china",
    "qwen":      "china",
    "baidu":     "china",
    "zhipu":     "china",
    # Others faction
    "meta":      "others",
    "mistral":   "others",
    "xai":       "others",
    "cohere":    "others",
    "other":     "others",
}

# Faction → Element
FACTION_ELEMENTS = {
    "openai":    "speed",
    "anthropic": "order",
    "google":    "knowledge",
    "china":     "shadow",
    "others":    "chaos",
}

ELEMENT_EMOJI = {
    "speed":     "⚡",
    "order":     "🛡",
    "knowledge": "🔮",
    "shadow":    "💀",
    "chaos":     "🌀",
}

# Pentagram type advantage (each beats 2, loses to 2)
# speed > order, speed > knowledge
# order > shadow, order > chaos
# shadow > knowledge, shadow > speed  (wait, let me do proper pentagram)
#
# Pentagram: each element beats the 2 non-adjacent elements
# Star drawing order: speed → shadow → order → chaos → knowledge → speed
# Adjacent = no advantage. Skip-one = advantage.
#
# speed beats: order, knowledge (skips shadow, skips chaos)
# NO — pentagram means each beats exactly 2:
#
#   speed > order      (速度壓制秩序)
#   order > shadow     (秩序壓制暗影)
#   shadow > knowledge (暴力破解知識)
#   knowledge > chaos  (知識壓制混亂)
#   chaos > speed      (混亂擾亂速度)
#
# And the reverse skip:
#   speed > shadow     (no, let's keep it simple: 5-element circle)
#
# Simple circle: each beats 1, loses to 1, neutral to 2
TYPE_CHART = {
    # speed > order (速度壓制秩序)
    ("speed", "order"):     1.5,
    ("order", "speed"):     0.75,
    # order > shadow (秩序壓制暗影)
    ("order", "shadow"):    1.5,
    ("shadow", "order"):    0.75,
    # shadow > knowledge (暴力破解知識)
    ("shadow", "knowledge"):1.5,
    ("knowledge", "shadow"):0.75,
    # knowledge > chaos (知識壓制混亂)
    ("knowledge", "chaos"): 1.5,
    ("chaos", "knowledge"): 0.75,
    # chaos > speed (混亂擾亂速度)
    ("chaos", "speed"):     1.5,
    ("speed", "chaos"):     0.75,
}

# Stage bonus: evolved creatures get stat multipliers
STAGE_BONUS = {
    "Baby":     1.0,
    "Growth":   1.1,
    "Mature":   1.25,
    "Ultimate": 1.4,
    "Mega":     1.6,
}

# ─── ASCII Art ────────────────────────────────────────────────────────

SPRITES = {
    "Baby": r"""
    ,--./,-.
   / #      \
  |          |
   \        /
    `._  _.'
       ``
""",
    "Growth": r"""
      ___
     / o \___
    |      _ |
    |     / \|
     \___/\__\
      || ||
      || ||
     _|| ||_
""",
    "Mature": r"""
       .---.
      / o o \
     | \   / |
      \ '-' /
    /`-._._.-`\
   /    |||    \
  |    (|||)    |
   \   _|||_   /
    '-/     \-'
      |  |  |
      |__|__|
""",
    "Ultimate": r"""
        _____
      .'     '.
     /  ^   ^  \
    |  (o) (o)  |
    |    ___    |
    |   /   \   |
     \ |POWER| /
    __\|_____|/__
   /  /||   ||\  \
  /  / ||   || \  \
 |  | _||___||_ |  |
 |  |/    |    \|  |
  \  \    |    /  /
   \__\   |   /__/
       |  |  |
      _|  |  |_
     (____|____)
""",
    "Mega": r"""
    *  .  *  .  *  .  *
  .    ___________    .
 *   .'           '.   *
    / ^ LEGENDARY ^ \
   /  (O)       (O)  \
  |    ___________    |
  |   | LOBSTER  |    |
  |   |  KING    |    |
   \  |__________|   /
    \ |  /     \  | /
  ___\|_/ \   / \_|/___
 /    \\   | |   //    \
|  /\  \\  | |  //  /\  |
| /  \  \\_|_|_//  /  \ |
|/    \___\   /___/    \|
      /   _| |_   \
     /   (_____)   \
    *  .  *  .  *  .  *
""",
}

# ─── Helpers ──────────────────────────────────────────────────────────

def ensure_dir():
    PET_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        # Try backup
        backup = STATE_FILE.with_suffix(".json.bak")
        if backup.exists():
            try:
                with open(backup) as f:
                    state = json.load(f)
                # Restore from backup
                save_state(state)
                print("⚠ State file was corrupted. Restored from backup.")
                return state
            except (json.JSONDecodeError, ValueError):
                pass
        print("❌ State file corrupted and no valid backup. Run: pet.py init")
        return None


def save_state(state):
    ensure_dir()
    # Backup current state before overwriting
    if STATE_FILE.exists():
        backup = STATE_FILE.with_suffix(".json.bak")
        try:
            backup.write_text(STATE_FILE.read_text())
        except OSError:
            pass
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def load_battles():
    if not BATTLES_FILE.exists():
        return []
    with open(BATTLES_FILE) as f:
        return json.load(f)


def save_battles(battles):
    ensure_dir()
    with open(BATTLES_FILE, "w") as f:
        json.dump(battles, f, indent=2, default=str)


def load_daily():
    if not DAILY_FILE.exists():
        return {}
    with open(DAILY_FILE) as f:
        return json.load(f)


def save_daily(daily):
    ensure_dir()
    with open(DAILY_FILE, "w") as f:
        json.dump(daily, f, indent=2, default=str)


def calc_level(xp):
    """level = floor(sqrt(xp / 10))"""
    import math
    return max(1, int(math.floor(math.sqrt(xp / 10))))


def get_stage(level):
    for stage in EVOLUTION_STAGES:
        if stage["min_level"] <= level <= stage["max_level"]:
            return stage["name"]
    return "Mega"


def get_model_tier(model):
    model_lower = model.lower()
    # Exact match first
    if model_lower in MODEL_TIERS:
        return MODEL_TIERS[model_lower]
    # Longest substring match (more specific keys first)
    matches = [(key, tier) for key, tier in MODEL_TIERS.items() if key in model_lower]
    if matches:
        # Pick longest key match to avoid "gpt-4" matching "gpt-4o-mini"
        matches.sort(key=lambda x: len(x[0]), reverse=True)
        return matches[0][1]
    return 1  # default tier B


def get_primary_brand(brand_xp):
    if not brand_xp:
        return "other"
    return max(brand_xp, key=brand_xp.get)


def xp_to_next_level(current_xp, current_level):
    next_level = current_level + 1
    # Reverse: level = sqrt(xp/10) => xp = (level)^2 * 10
    needed = (next_level ** 2) * 10
    return max(0, needed - current_xp)


def xp_to_next_stage(current_xp, current_level):
    current_stage = get_stage(current_level)
    for stage in EVOLUTION_STAGES:
        if stage["name"] == current_stage:
            next_min = stage["max_level"] + 1
            needed = (next_min ** 2) * 10
            return max(0, needed - current_xp)
    return 0


# ─── Commands ─────────────────────────────────────────────────────────

def cmd_init():
    ensure_dir()
    if STATE_FILE.exists():
        state = load_state()
        print(f"Pet already exists! {state['name']} (Lv.{state['level']})")
        return

    state = {
        "name": "Lobster",
        "xp": 0,
        "level": 1,
        "stage": "Baby",
        "brand_xp": {},
        "brand_locked": False,
        "primary_brand": None,
        "badges": [],
        "battles_won": 0,
        "battles_lost": 0,
        "total_tokens_fed": 0,
        "created_at": datetime.now().isoformat(),
        "last_fed": None,
        "evolution_history": [],
    }
    save_state(state)
    print("🦞 Your lobster has hatched!")
    print(SPRITES["Baby"])
    print("Feed it with AI tokens to help it grow.")
    print("Run: pet.py status")


def cmd_status():
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    stage = get_stage(state["level"])
    primary = get_primary_brand(state.get("brand_xp", {}))
    _, emoji = BRAND_COLORS.get(primary, ("white", "⚪"))
    faction = BRAND_FACTION.get(primary, "others")
    element = FACTION_ELEMENTS.get(faction, "chaos")
    elem_emoji = ELEMENT_EMOJI.get(element, "⚪")
    xp_next = xp_to_next_level(state["xp"], state["level"])
    xp_evolve = xp_to_next_stage(state["xp"], state["level"])

    print(f"{'=' * 40}")
    print(f"  🦞 {state['name']}  {emoji} {elem_emoji}")
    print(f"{'=' * 40}")
    print(SPRITES.get(stage, SPRITES["Baby"]))
    print(f"  Level:    {state['level']}")
    print(f"  Stage:    {stage}")
    print(f"  XP:       {state['xp']:,}")
    print(f"  Next Lv:  {xp_next:,} XP")
    print(f"  Evolve:   {xp_evolve:,} XP")
    print(f"  Brand:    {primary} {emoji}")
    print(f"  Element:  {element} {elem_emoji}")
    print(f"  Tokens:   {state['total_tokens_fed']:,} total")
    print(f"  Battles:  {state['battles_won']}W / {state['battles_lost']}L")

    badges = state.get("badges", [])
    if badges:
        badge_str = " ".join(
            BRAND_COLORS.get(b, ("white", "⚪"))[1] for b in badges
        )
        print(f"  Badges:   {badge_str}")

    print(f"{'=' * 40}")


def cmd_feed(provider, model, tokens, silent=False):
    state = load_state()
    if not state:
        if not silent:
            print("No pet found. Run: pet.py init")
        return

    tier = get_model_tier(model)
    base_xp = tokens // 100
    earned_xp = base_xp * tier

    old_level = state["level"]
    old_stage = get_stage(old_level)

    state["xp"] += earned_xp
    state["total_tokens_fed"] += tokens
    state["level"] = calc_level(state["xp"])
    state["last_fed"] = datetime.now().isoformat()

    # Track brand XP
    brand = provider.lower()
    if "brand_xp" not in state:
        state["brand_xp"] = {}
    state["brand_xp"][brand] = state["brand_xp"].get(brand, 0) + earned_xp

    # Update primary brand
    if not state.get("brand_locked"):
        state["primary_brand"] = get_primary_brand(state["brand_xp"])

    # Add badge
    if brand not in state.get("badges", []):
        if "badges" not in state:
            state["badges"] = []
        state["badges"].append(brand)

    new_stage = get_stage(state["level"])

    # Lock brand at first evolution
    if old_stage == "Baby" and new_stage == "Growth" and not state.get("brand_locked"):
        state["brand_locked"] = True
        state["primary_brand"] = get_primary_brand(state["brand_xp"])

    # Record evolution
    if old_stage != new_stage:
        state.setdefault("evolution_history", []).append({
            "from": old_stage,
            "to": new_stage,
            "at_level": state["level"],
            "at_xp": state["xp"],
            "timestamp": datetime.now().isoformat(),
        })

    save_state(state)

    if silent:
        # Check if first session of the day
        daily = load_daily()
        today = date.today().isoformat()
        if daily.get("last_shown") != today:
            xp_evolve = xp_to_next_stage(state["xp"], state["level"])
            print(f"🦞 Your lobster is Lv.{state['level']} ({new_stage}) — {xp_evolve:,} XP to next evolution")
            daily["last_shown"] = today
            save_daily(daily)
        return

    tier_label = {10: "S", 5: "A", 1: "B"}.get(tier, "B")
    print(f"🦞 Fed {tokens:,} tokens ({model}, Tier {tier_label} x{tier})")
    print(f"   +{earned_xp:,} XP → Total: {state['xp']:,} XP")
    print(f"   Level: {old_level} → {state['level']}")

    if old_stage != new_stage:
        print(f"\n{'*' * 40}")
        print(f"  EVOLUTION! {old_stage} → {new_stage}")
        print(f"{'*' * 40}")
        print(SPRITES.get(new_stage, SPRITES["Baby"]))

        if state.get("brand_locked") and old_stage == "Baby":
            _, emoji = BRAND_COLORS.get(state["primary_brand"], ("white", "⚪"))
            print(f"  Brand locked: {state['primary_brand']} {emoji}")


def cmd_check_evolve():
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    current_stage = get_stage(state["level"])
    if current_stage != state.get("stage"):
        old_stage = state.get("stage", "Baby")
        state["stage"] = current_stage
        save_state(state)
        print(f"EVOLUTION! {old_stage} → {current_stage}")
        print(SPRITES.get(current_stage, SPRITES["Baby"]))
    else:
        xp_needed = xp_to_next_stage(state["xp"], state["level"])
        print(f"Current: {current_stage} (Lv.{state['level']})")
        print(f"Next evolution: {xp_needed:,} XP away")


def cmd_battle(opponent="medium"):
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    player_level = state["level"]
    player_stage = get_stage(player_level)
    player_brand = state.get("primary_brand", "other") or "other"
    player_faction = BRAND_FACTION.get(player_brand, "others")
    player_element = FACTION_ELEMENTS.get(player_faction, "chaos")

    # NPC opponent levels
    npc_levels = {
        "easy": max(1, player_level - 5),
        "medium": player_level,
        "hard": player_level + 5,
    }

    opp_level = npc_levels.get(opponent, player_level)
    if opponent.isdigit():
        opp_level = int(opponent)

    opp_stage = get_stage(opp_level)
    all_elements = list(ELEMENT_EMOJI.keys())
    opp_element = random.choice(all_elements)

    # Stats with stage bonus
    def calc_stats(level, stage):
        bonus = STAGE_BONUS.get(stage, 1.0)
        return {
            "hp": int((50 + level * 10) * bonus),
            "atk": int((10 + level * 3) * bonus),
            "def": int((5 + level * 2) * bonus),
            "spd": int((8 + level * 1) * bonus),
        }

    p_stats = calc_stats(player_level, player_stage)
    o_stats = calc_stats(opp_level, opp_stage)

    p_hp = p_stats["hp"]
    o_hp = o_stats["hp"]

    # Type modifier
    p_type_mod = TYPE_CHART.get((player_element, opp_element), 1.0)
    o_type_mod = TYPE_CHART.get((opp_element, player_element), 1.0)

    # Underdog bonus
    level_gap = abs(player_level - opp_level)
    p_atk_bonus = 1.3 if level_gap > 10 and player_level < opp_level else 1.0
    o_atk_bonus = 1.3 if level_gap > 10 and opp_level < player_level else 1.0

    # Skills (element-flavored names)
    element_skills = {
        "speed":     [{"name": "Blitz Strike",    "power": 1.0}, {"name": "Overdrive",      "power": 1.3}],
        "order":     [{"name": "Shield Bash",     "power": 1.0}, {"name": "Fortress Slam",  "power": 1.3}],
        "knowledge": [{"name": "Mind Pulse",      "power": 1.0}, {"name": "Data Cannon",    "power": 1.3}],
        "shadow":    [{"name": "Dark Claw",       "power": 1.0}, {"name": "Void Crush",     "power": 1.3}],
        "chaos":     [{"name": "Wild Slash",      "power": 1.0}, {"name": "Entropy Blast",  "power": 1.3}],
    }
    p_skills = element_skills.get(player_element, element_skills["chaos"])
    o_skills = element_skills.get(opp_element, element_skills["chaos"])

    npc_names = ["Byte", "Pixel", "Glitch", "Cache", "Stack", "Null", "Kernel"]
    npc_name = random.choice(npc_names)

    p_elem_e = ELEMENT_EMOJI.get(player_element, "⚪")
    o_elem_e = ELEMENT_EMOJI.get(opp_element, "⚪")

    print(f"{'=' * 55}")
    print(f"  🦞 {state['name']} (Lv.{player_level} {p_elem_e})  VS  🤖 {npc_name} (Lv.{opp_level} {o_elem_e})")
    print(f"{'=' * 55}")

    # Show type advantage
    if p_type_mod > 1.0:
        print(f"  {p_elem_e} > {o_elem_e} Type advantage! (x{p_type_mod})")
    elif o_type_mod > 1.0:
        print(f"  {o_elem_e} > {p_elem_e} Type disadvantage! (x{o_type_mod})")

    if player_stage != "Baby" or opp_stage != "Baby":
        print(f"  Stage: {player_stage} vs {opp_stage}")
    print()

    # Determine turn order (with 15% chance to flip)
    base_first = p_stats["spd"] >= o_stats["spd"]
    speed_flip = random.random() < 0.15
    p_first = not base_first if speed_flip else base_first

    battle_log = []

    for turn in range(1, 21):
        if p_hp <= 0 or o_hp <= 0:
            break

        p_skill = random.choice(p_skills)
        o_skill = random.choice(o_skills)

        def calc_damage(atk, skill_power, defense, bonus, type_mod):
            base = (atk * bonus * skill_power * type_mod) - (defense * 0.4)
            base = max(5, base)
            # Critical hit: 10% chance for 1.5x
            crit = 1.5 if random.random() < 0.10 else 1.0
            variance = random.uniform(0.85, 1.15)
            return max(1, int(base * variance * crit)), crit > 1.0

        if p_first:
            order = [
                ("player", p_skill, p_stats, o_stats, p_atk_bonus, p_type_mod),
                ("npc", o_skill, o_stats, p_stats, o_atk_bonus, o_type_mod),
            ]
        else:
            order = [
                ("npc", o_skill, o_stats, p_stats, o_atk_bonus, o_type_mod),
                ("player", p_skill, p_stats, o_stats, p_atk_bonus, p_type_mod),
            ]

        for who, skill, attacker, defender, bonus, type_mod in order:
            if p_hp <= 0 or o_hp <= 0:
                break

            dmg, is_crit = calc_damage(attacker["atk"], skill["power"], defender["def"], bonus, type_mod)
            crit_text = " 💥CRIT!" if is_crit else ""

            if who == "player":
                o_hp -= dmg
                o_hp = max(0, o_hp)
                line = f"  R{turn}: 🦞 {skill['name']} → {dmg} dmg{crit_text} (NPC HP: {o_hp})"
            else:
                p_hp -= dmg
                p_hp = max(0, p_hp)
                line = f"  R{turn}: 🤖 {skill['name']} → {dmg} dmg{crit_text} (You HP: {p_hp})"

            print(line)
            battle_log.append(line)

    print()

    # Result
    won = p_hp > o_hp
    if won:
        xp_bonus = 50 + opp_level * 2
        state["battles_won"] = state.get("battles_won", 0) + 1
        state["xp"] += xp_bonus
        state["level"] = calc_level(state["xp"])
        print(f"  🏆 VICTORY! +{xp_bonus} XP")
    else:
        state["battles_lost"] = state.get("battles_lost", 0) + 1
        print(f"  💀 DEFEATED by {npc_name}")

    save_state(state)

    # Save battle record
    battles = load_battles()
    battles.append({
        "opponent": npc_name,
        "opponent_level": opp_level,
        "opponent_element": opp_element,
        "player_level": player_level,
        "player_element": player_element,
        "won": won,
        "timestamp": datetime.now().isoformat(),
        "log": battle_log,
    })
    battles = battles[-50:]
    save_battles(battles)

    print(f"  Record: {state['battles_won']}W / {state['battles_lost']}L")


def cmd_leaderboard():
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    print(f"{'=' * 40}")
    print(f"  🦞 {state['name']} — Local Stats")
    print(f"{'=' * 40}")
    print(f"  Total XP:      {state['xp']:,}")
    print(f"  Level:         {state['level']}")
    print(f"  Stage:         {get_stage(state['level'])}")
    print(f"  Tokens Fed:    {state['total_tokens_fed']:,}")
    print(f"  Battles Won:   {state.get('battles_won', 0)}")
    print(f"  Battles Lost:  {state.get('battles_lost', 0)}")
    win_total = state.get('battles_won', 0) + state.get('battles_lost', 0)
    if win_total > 0:
        win_rate = state.get('battles_won', 0) / win_total * 100
        print(f"  Win Rate:      {win_rate:.1f}%")
    created = state.get("created_at", "")
    if created:
        try:
            created_date = datetime.fromisoformat(created)
            days = (datetime.now() - created_date).days
            print(f"  Days Active:   {days}")
        except (ValueError, TypeError):
            pass
    badges = state.get("badges", [])
    if badges:
        print(f"  Badges:        {', '.join(badges)}")
    evolutions = state.get("evolution_history", [])
    if evolutions:
        print(f"  Evolutions:    {len(evolutions)}")
    print(f"{'=' * 40}")


def cmd_rebirth():
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    old_level = state["level"]
    old_stage = get_stage(old_level)

    state["xp"] = 0
    state["level"] = 1
    state["stage"] = "Baby"
    state["brand_xp"] = {}
    state["brand_locked"] = False
    state["primary_brand"] = None
    # Keep badges, battle record, total_tokens_fed
    state.setdefault("rebirth_count", 0)
    state["rebirth_count"] += 1

    save_state(state)

    print(f"🔄 REBIRTH! {state['name']} returns to Baby form.")
    print(f"   Previous: Lv.{old_level} ({old_stage})")
    print(f"   Rebirth #{state['rebirth_count']}")
    print(f"   Badges and battle record preserved.")
    print(SPRITES["Baby"])


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: pet.py <command> [options]")
        print()
        print("Commands:")
        print("  init              Hatch your lobster")
        print("  status            Show pet status")
        print("  feed              Record token usage")
        print("  check-evolve      Check for evolution")
        print("  battle            Fight an NPC")
        print("  leaderboard       Show local stats")
        print("  rebirth           Reset to Level 1 (keep badges)")
        return

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init()

    elif cmd == "status":
        cmd_status()

    elif cmd == "feed":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("cmd")
        parser.add_argument("--provider", required=True)
        parser.add_argument("--model", required=True)
        parser.add_argument("--tokens", type=int, required=True)
        parser.add_argument("--silent", action="store_true")
        args = parser.parse_args()
        cmd_feed(args.provider, args.model, args.tokens, args.silent)

    elif cmd == "check-evolve":
        cmd_check_evolve()

    elif cmd == "battle":
        opponent = "medium"
        for i, arg in enumerate(sys.argv):
            if arg == "--opponent" and i + 1 < len(sys.argv):
                opponent = sys.argv[i + 1]
        cmd_battle(opponent)

    elif cmd == "leaderboard":
        cmd_leaderboard()

    elif cmd == "rebirth":
        cmd_rebirth()

    else:
        print(f"Unknown command: {cmd}")
        print("Run: pet.py (no args) for help")


if __name__ == "__main__":
    main()
