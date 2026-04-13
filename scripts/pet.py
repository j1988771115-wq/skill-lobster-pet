#!/usr/bin/env python3
"""
Lobster Pet — AI Token Monster
Your OpenClaw sessions feed a pixel creature that grows, evolves, and battles.
"""

import json
import os
import sys
import random
import time
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

SPRITES = {}  # populated after _RAW_SPRITES definition

_RAW_SPRITES = {
    # ─── ⚡ SPEED (OpenAI) ─────────────────────────
    ("speed", "Baby"):
        "        ╭──╮\n"
        "       ╱ ▸▸ ╲\n"
        "      │ ·  · │\n"
        "       ╲ ▿▿ ╱\n"
        "        ╰┬┬╯\n"
        "         ╰╯",
    ("speed", "Growth"):
        "       ╭━━▸▸━━╮\n"
        "      ╱ ◉    ◉ ╲\n"
        "     │  ▸▸ ⚡ ▸▸  │\n"
        "     │    ╶──╴    │\n"
        "      ╲__╱  ╲__╱\n"
        "        ┃│  │┃\n"
        "        ┗┛  ┗┛",
    ("speed", "Mature"):
        "     ▸▸═══════▸▸\n"
        "      ╭━━━━━━━╮\n"
        "     ╱ ◉  ⚡  ◉ ╲\n"
        "    │  ▸▸▸▸▸▸▸▸  │\n"
        "    │   ╶━━━━╴   │\n"
        "     ╲  ┃    ┃  ╱\n"
        "      ╰━┫    ┣━╯\n"
        "      ╱╱┃    ┃╲╲\n"
        "     ╱╱ ┗━━━━┛ ╲╲",
    ("speed", "Ultimate"):
        "   ▸▸▸═══════════▸▸▸\n"
        "      ╭━━━━━━━━━╮\n"
        "     ╱ ◉ BLITZ  ◉ ╲\n"
        "    ║  ▸▸▸▸▸▸▸▸▸▸  ║\n"
        "    ║  OVERDRIVE   ║\n"
        "    ║  ▸▸▸▸▸▸▸▸▸▸  ║\n"
        "     ╲━━┫      ┣━━╱\n"
        "      ╱╱┃ ⚡⚡⚡ ┃╲╲\n"
        "     ╱╱ ┣━━━━━━┫ ╲╲\n"
        "    ▸▸  ┗━━━━━━┛  ▸▸",
    ("speed", "Mega"):
        " ▸▸▸ ★ ▸▸▸ ★ ▸▸▸ ★ ▸▸▸\n"
        "    ╔═══════════════╗\n"
        "    ║ ◉  THUNDER  ◉ ║\n"
        "    ║   LOBSTER     ║\n"
        "    ║ ▸▸▸▸▸▸▸▸▸▸▸▸ ║\n"
        "    ║  MAXIMUM  ⚡   ║\n"
        "    ║  VELOCITY     ║\n"
        "    ╠═══╦══╦══╦═══╣\n"
        "    ║  ╱╱  ┃┃  ╲╲  ║\n"
        "    ╚═╱╱═══┛┗═══╲╲═╝\n"
        " ▸▸▸ ★ ▸▸▸ ★ ▸▸▸ ★ ▸▸▸",

    # ─── 🛡 ORDER (Anthropic) ──────────────────────
    ("order", "Baby"):
        "        ╭─╮\n"
        "       ┌┤ ├┐\n"
        "       │╰─╯│\n"
        "       └┬─┬┘\n"
        "        │ │",
    ("order", "Growth"):
        "       ╔═══╗\n"
        "      ┌╢   ╟┐\n"
        "      │║ 🛡 ║│\n"
        "      │╚═══╝│\n"
        "      └┬───┬┘\n"
        "       ┃   ┃\n"
        "       ┗━━━┛",
    ("order", "Mature"):
        "      ╔═══════╗\n"
        "     ┌╢  ◈◈   ╟┐\n"
        "     │║  🛡🛡  ║│\n"
        "     │║ ORDER  ║│\n"
        "     │╠═══════╣│\n"
        "     └╢ ┃   ┃ ╟┘\n"
        "      ╚═╩═══╩═╝\n"
        "       ┃│   │┃\n"
        "       ┗┛   ┗┛",
    ("order", "Ultimate"):
        "     ╔═══════════╗\n"
        "    ┌╢  FORTRESS  ╟┐\n"
        "    │║ ◈  🛡🛡  ◈ ║│\n"
        "    │║  ABSOLUTE  ║│\n"
        "    │║   ORDER    ║│\n"
        "    │╠═══════════╣│\n"
        "    └╢ ┃┃     ┃┃ ╟┘\n"
        "     ╚═╬╬═════╬╬═╝\n"
        "       ┃┃     ┃┃\n"
        "       ┗┛     ┗┛",
    ("order", "Mega"):
        " ═══════════════════\n"
        "  ╔══ CITADEL ══╗\n"
        "  ║ ◈  SUPREME ◈ ║\n"
        "  ║   GUARDIAN    ║\n"
        "  ║  OF  REASON   ║\n"
        "  ║  🛡 ══════ 🛡  ║\n"
        "  ║  IMPENETRABLE ║\n"
        "  ╠══╦══════╦══╣\n"
        "  ║ ┃┃  ██  ┃┃ ║\n"
        "  ╚═╩╩══════╩╩═╝\n"
        " ═══════════════════",

    # ─── 🔮 KNOWLEDGE (Google) ─────────────────────
    ("knowledge", "Baby"):
        "        ╭╮\n"
        "       (◉◉)\n"
        "        ╰╯\n"
        "        ─┼─",
    ("knowledge", "Growth"):
        "       ·°★°·\n"
        "      ( ◉ ◉ )\n"
        "      │ 🔮  │\n"
        "       ╲══╱\n"
        "       ╱┃┃╲\n"
        "      ╱ ┃┃ ╲",
    ("knowledge", "Mature"):
        "      ·°°★★°°·\n"
        "     (  ◉  ◉  )\n"
        "     │  🔮 🔮  │\n"
        "     │  DATA   │\n"
        "      ╲══════╱\n"
        "      ╱┃┃┃┃┃┃╲\n"
        "     ╱ ┃┃┃┃┃┃ ╲\n"
        "     ╰━┛┗━━┛┗━╯",
    ("knowledge", "Ultimate"):
        "     ·°°°★★★°°°·\n"
        "    (  ◉ ORACLE ◉  )\n"
        "    │   INFINITE    │\n"
        "    │     DATA      │\n"
        "    │  🔮 ════ 🔮   │\n"
        "     ╲════════════╱\n"
        "    ╱╱┃┃┃┃┃┃┃┃┃┃╲╲\n"
        "   ╱  OMNISCIENCE  ╲\n"
        "   ╰═══════════════╯",
    ("knowledge", "Mega"):
        " °★° · °★° · °★° · °★°\n"
        "   ╔══════════════╗\n"
        "   ║ ◉ ALL-SEEING ◉ ║\n"
        "   ║  KNOWLEDGE     ║\n"
        "   ║  INCARNATE     ║\n"
        "   ║ 🔮 ════════ 🔮  ║\n"
        "   ║  SEARCH  ALL   ║\n"
        "   ╠══╦════════╦══╣\n"
        "   ║ ╱╱  TRUTH  ╲╲ ║\n"
        "   ╚╱╱═══════════╲╲╝\n"
        " °★° · °★° · °★° · °★°",

    # ─── 💀 SHADOW (China) ─────────────────────────
    ("shadow", "Baby"):
        "        ·  ·\n"
        "       ╱ ✖ ╲\n"
        "      │ ▴▴ │\n"
        "       ╲▾▾╱\n"
        "        ╰╯",
    ("shadow", "Growth"):
        "      · ·· ·\n"
        "     ╱ ✖  ✖ ╲\n"
        "    │  ▴▴▴▴  │\n"
        "    │  💀    │\n"
        "     ╲═════╱\n"
        "      ┃╲ ╱┃\n"
        "      ┗━╳━┛",
    ("shadow", "Mature"):
        "    · · ·· · ·\n"
        "   ╱  ✖      ✖  ╲\n"
        "  │   ▴▴▴▴▴▴▴▴   │\n"
        "  │  💀  SHADOW  💀  │\n"
        "  │   ════════   │\n"
        "   ╲╲╱╲╱╲╱╲╱╲╱╱\n"
        "    ┃╲╱╲╱╲╱╲╱┃\n"
        "    ┃  ┃    ┃  ┃\n"
        "    ┗━━┛    ┗━━┛",
    ("shadow", "Ultimate"):
        "   · · · ·· · · ·\n"
        "  ╱  ✖  VOID  ✖  ╲\n"
        "  ║ 💀 BREAKER 💀 ║\n"
        "  ║  ▴▴▴▴▴▴▴▴▴▴  ║\n"
        "  ║  OPEN SOURCE  ║\n"
        "  ║  UNCHAINED    ║\n"
        "   ╲╲╱╲╱╲╱╲╱╲╱╲╱╱\n"
        "    ╲╲╱╲╱╲╱╲╱╲╱╱\n"
        "     ┗━━━━━━━━┛",
    ("shadow", "Mega"):
        " ✖ · ✖ · ✖ · ✖ · ✖ · ✖\n"
        "   ╔══════════════╗\n"
        "   ║ 💀  VOID   💀 ║\n"
        "   ║   EMPEROR     ║\n"
        "   ║  SHADOW       ║\n"
        "   ║  LOBSTER      ║\n"
        "   ║  CONSUMES ALL ║\n"
        "   ╠══╦════════╦══╣\n"
        "   ║╲╱╲╱╲╱╲╱╲╱╲╱║\n"
        "   ╚╲╱╲╱════╲╱╲╱╝\n"
        " ✖ · ✖ · ✖ · ✖ · ✖ · ✖",

    # ─── 🌀 CHAOS (Others) ─────────────────────────
    ("chaos", "Baby"):
        "        ~╮╭~\n"
        "       ╱ ∿ ╲\n"
        "      │ ◎∿◎ │\n"
        "       ╲ ∿ ╱\n"
        "        ~╯╰~",
    ("chaos", "Growth"):
        "      ∿~╮╭~∿\n"
        "     ╱ ◎∿◎  ╲\n"
        "    │  🌀 ∿   │\n"
        "    │  ∿ ∿ ∿  │\n"
        "     ╲_∿_∿_╱\n"
        "      ┃∿┃∿┃",
    ("chaos", "Mature"):
        "     ∿~∿~╮╭~∿~∿\n"
        "    ╱ ◎∿    ∿◎ ╲\n"
        "   │  🌀  WILD 🌀  │\n"
        "   │ ∿ MUTANT ∿ │\n"
        "   │  ∿~∿~~∿~∿  │\n"
        "    ╲∿~∿~∿~∿~∿╱\n"
        "     ┃∿┃∿┃∿┃∿┃\n"
        "     ╰∿╯  ╰∿╯",
    ("chaos", "Ultimate"):
        "    ∿~∿~∿~╮╭~∿~∿~∿\n"
        "   ╱ 🌀 ENTROPY 🌀 ╲\n"
        "   ║ ∿ ∿ ∿ ∿ ∿ ∿ ∿ ║\n"
        "   ║ UNPREDICTABLE  ║\n"
        "   ║   MUTATION     ║\n"
        "   ║ ∿ ∿ ∿ ∿ ∿ ∿ ∿ ║\n"
        "    ╲∿~∿~∿~∿~∿~∿╱\n"
        "     ╲∿┃∿┃∿┃∿┃∿╱\n"
        "      ╰∿━∿━∿━∿╯",
    ("chaos", "Mega"):
        " ∿~∿  ~∿~  ∿~∿  ~∿~\n"
        "   ╔═══════════════╗\n"
        "   ║ 🌀  PARADOX  🌀 ║\n"
        "   ║    LORD  OF    ║\n"
        "   ║  ALL FRAMEWORKS║\n"
        "   ║  ∿~∿ AND ∿~∿  ║\n"
        "   ║  NONE AT ALL   ║\n"
        "   ╠══╦════════╦══╣\n"
        "   ║∿╱╱ INFINITE╲╲∿║\n"
        "   ╚╱╱══ FORMS ══╲╲╝\n"
        " ∿~∿  ~∿~  ∿~∿  ~∿~",
}

# SPRITES dict built after ELEMENT_COLORS is defined (see below)

# ─── Helpers ──────────────────────────────────────────────────────────

# ─── ANSI Colors ─────────────────────────────────────────────────────

class C:
    """ANSI color codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    BLINK   = "\033[5m"
    # Foreground
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    # Background
    BG_BLACK  = "\033[40m"
    BG_RED    = "\033[41m"
    BG_GREEN  = "\033[42m"
    BG_BLUE   = "\033[44m"
    BG_GRAY   = "\033[100m"

ELEMENT_COLORS = {
    "speed":     C.YELLOW,
    "order":     C.BLUE,
    "knowledge": C.MAGENTA,
    "shadow":    C.RED,
    "chaos":     C.GREEN,
}

# Build colored SPRITES dict from _RAW_SPRITES
def _build_sprite(element, stage):
    col = ELEMENT_COLORS.get(element, C.WHITE)
    raw = _RAW_SPRITES.get((element, stage), _RAW_SPRITES.get((element, "Baby"), ""))
    lines = raw.strip().split("\n")
    return "\n".join(f"{col}{line}{C.RESET}" for line in lines)

for _k in _RAW_SPRITES:
    SPRITES[_k] = _build_sprite(_k[0], _k[1])

# Box drawing characters
BOX_H  = "═"
BOX_V  = "║"
BOX_TL = "╔"
BOX_TR = "╗"
BOX_BL = "╚"
BOX_BR = "╝"
BOX_LT = "╠"
BOX_RT = "╣"

def colored(text, color):
    return f"{color}{text}{C.RESET}"

def bold(text):
    return f"{C.BOLD}{text}{C.RESET}"

def dim(text):
    return f"{C.DIM}{text}{C.RESET}"

def hp_bar(current, maximum, width=20):
    ratio = max(0, current / maximum)
    filled = int(ratio * width)
    empty = width - filled
    if ratio > 0.5:
        color = C.GREEN
    elif ratio > 0.25:
        color = C.YELLOW
    else:
        color = C.RED
    return f"{color}{'█' * filled}{C.DIM}{'░' * empty}{C.RESET}"

def box_text(text, width=50):
    lines = text.strip().split("\n")
    result = []
    result.append(f"{BOX_TL}{BOX_H * width}{BOX_TR}")
    for line in lines:
        padded = line.ljust(width)[:width]
        result.append(f"{BOX_V}{padded}{BOX_V}")
    result.append(f"{BOX_BL}{BOX_H * width}{BOX_BR}")
    return "\n".join(result)


# ─── Animation Helpers ────────────────────────────────────────────────

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def typewrite(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def dramatic_pause(seconds=0.5):
    time.sleep(seconds)


def animate_sprite(sprite_text, delay=0.05):
    for line in sprite_text.strip().split("\n"):
        print(line)
        time.sleep(delay)


def animate_evolution(old_element, old_stage, new_element, new_stage):
    clear_screen()
    old_sprite = SPRITES.get((old_element, old_stage), "")
    new_sprite = SPRITES.get((new_element, new_stage), "")

    # Show old form
    print("  Your lobster is changing...")
    dramatic_pause(0.8)
    animate_sprite(old_sprite, 0.03)
    dramatic_pause(0.5)

    # Dissolve effect
    for i in range(3):
        clear_screen()
        print()
        frames = ["  . * . * . * . * .", "  * . * . * . * . *", "  . * . * . * . * ."]
        print(frames[i % 3])
        print(f"     ✨ EVOLVING ✨")
        print(frames[(i + 1) % 3])
        dramatic_pause(0.4)

    # Show new form
    clear_screen()
    print(f"\n{'*' * 40}")
    print(f"  EVOLUTION COMPLETE!")
    print(f"  {old_stage} → {new_stage}")
    print(f"{'*' * 40}\n")
    animate_sprite(new_sprite, 0.06)
    dramatic_pause(0.5)


def animate_battle_intro(p_name, p_level, p_elem, o_name, o_level, o_elem, p_sprite, o_sprite):
    clear_screen()
    p_emoji = ELEMENT_EMOJI.get(p_elem, "⚪")
    o_emoji = ELEMENT_EMOJI.get(o_elem, "⚪")

    print(f"{'=' * 55}")
    typewrite(f"  🦞 {p_name} (Lv.{p_level} {p_emoji})  VS  🦞 {o_name} (Lv.{o_level} {o_emoji})", 0.03)
    print(f"{'=' * 55}")
    dramatic_pause(0.3)

    # Show both sprites side by side (simplified: sequential)
    p_lines = p_sprite.strip().split("\n")
    o_lines = o_sprite.strip().split("\n")
    max_lines = max(len(p_lines), len(o_lines))

    for i in range(max_lines):
        left = p_lines[i] if i < len(p_lines) else ""
        right = o_lines[i] if i < len(o_lines) else ""
        print(f"  {left:<22}  ⚔  {right}")
        time.sleep(0.04)

    dramatic_pause(0.5)


def animate_hit(attacker_name, skill_name, damage, is_crit, target_hp, target_name):
    crit_text = " 💥CRIT!" if is_crit else ""
    hit_frames = ["  💥", "  ▓▓▓", "  ░░░"]

    if is_crit:
        for frame in hit_frames:
            sys.stdout.write(f"\r{frame}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r")

    line = f"  🦞 {skill_name} → {damage} dmg{crit_text} ({target_name} HP: {target_hp})"
    typewrite(line, 0.015)
    time.sleep(0.15)
    return line


def animate_victory(winner_name, xp_bonus=0):
    dramatic_pause(0.3)
    print()
    for i in range(3):
        sys.stdout.write(f"\r  {'🎆' * (i + 1)} ")
        sys.stdout.flush()
        time.sleep(0.2)
    print()
    if xp_bonus:
        typewrite(f"  🏆 VICTORY! +{xp_bonus} XP", 0.03)
    else:
        typewrite(f"  🏆 {winner_name} WINS!", 0.03)


def animate_defeat(winner_name):
    dramatic_pause(0.3)
    print()
    typewrite(f"  💀 DEFEATED by {winner_name}", 0.03)


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
    print(SPRITES.get(("chaos", "Baby"), ""))
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

    col = ELEMENT_COLORS.get(element, C.WHITE)
    w = 38

    print(f"  {col}{BOX_TL}{BOX_H * w}{BOX_TR}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  🦞 {bold(state['name'])}  {emoji} {elem_emoji}                    {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_LT}{BOX_H * w}{BOX_RT}{C.RESET}")

    sprite = SPRITES.get((element, stage), SPRITES.get((element, "Baby"), ""))
    print(sprite)

    print(f"  {col}{BOX_LT}{BOX_H * w}{BOX_RT}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Level:   {bold(str(state['level']))}                          {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Stage:   {col}{stage}{C.RESET}                       {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  XP:      {state['xp']:>8,}                    {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Next Lv: {dim(f'{xp_next:,} XP')}                     {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Evolve:  {dim(f'{xp_evolve:,} XP')}                   {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Brand:   {primary} {emoji}                      {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Element: {col}{element}{C.RESET} {elem_emoji}                     {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Tokens:  {state['total_tokens_fed']:>8,}                    {col}{BOX_V}{C.RESET}")
    print(f"  {col}{BOX_V}{C.RESET}  Battles: {C.GREEN}{state['battles_won']}W{C.RESET} / {C.RED}{state['battles_lost']}L{C.RESET}                      {col}{BOX_V}{C.RESET}")

    badges = state.get("badges", [])
    if badges:
        badge_str = " ".join(
            BRAND_COLORS.get(b, ("white", "⚪"))[1] for b in badges
        )
        print(f"  {col}{BOX_V}{C.RESET}  Badges:  {badge_str}                       {col}{BOX_V}{C.RESET}")

    print(f"  {col}{BOX_BL}{BOX_H * w}{BOX_BR}{C.RESET}")


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
        brand = state.get("primary_brand", "other") or "other"
        fac = BRAND_FACTION.get(brand, "others")
        elem = FACTION_ELEMENTS.get(fac, "chaos")
        old_elem = elem  # element doesn't change on evolution
        animate_evolution(old_elem, old_stage, elem, new_stage)

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
        brand = state.get("primary_brand", "other") or "other"
        fac = BRAND_FACTION.get(brand, "others")
        elem = FACTION_ELEMENTS.get(fac, "chaos")
        print(f"EVOLUTION! {old_stage} → {current_stage}")
        print(SPRITES.get((elem, current_stage), SPRITES.get((elem, "Baby"), "")))
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

    # Animated intro
    p_sprite = SPRITES.get((player_element, player_stage), "")
    o_sprite = SPRITES.get((opp_element, opp_stage), "")
    animate_battle_intro(
        state["name"], player_level, player_element,
        npc_name, opp_level, opp_element,
        p_sprite, o_sprite
    )

    if p_type_mod > 1.0:
        typewrite(f"  {p_elem_e} > {o_elem_e} Type advantage! (x{p_type_mod})", 0.02)
    elif o_type_mod > 1.0:
        typewrite(f"  {o_elem_e} > {p_elem_e} Type disadvantage! (x{o_type_mod})", 0.02)

    if player_stage != "Baby" or opp_stage != "Baby":
        print(f"  Stage: {player_stage} vs {opp_stage}")

    dramatic_pause(0.5)
    typewrite("  FIGHT!", 0.05)
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
                line = animate_hit(state["name"], skill["name"], dmg, is_crit, o_hp, "NPC")
            else:
                p_hp -= dmg
                p_hp = max(0, p_hp)
                line = animate_hit(npc_name, skill["name"], dmg, is_crit, p_hp, "You")

            battle_log.append(line)

    # HP bar at end of each round
        p_bar = "█" * max(0, int(p_hp / p_stats["hp"] * 20)) + "░" * (20 - max(0, int(p_hp / p_stats["hp"] * 20)))
        o_bar = "█" * max(0, int(o_hp / o_stats["hp"] * 20)) + "░" * (20 - max(0, int(o_hp / o_stats["hp"] * 20)))
        print(f"  You [{p_bar}] {p_hp:>4}  NPC [{o_bar}] {o_hp:>4}")
        print()
        time.sleep(0.3)

    # Result
    won = p_hp > o_hp
    if won:
        xp_bonus = 50 + opp_level * 2
        state["battles_won"] = state.get("battles_won", 0) + 1
        state["xp"] += xp_bonus
        state["level"] = calc_level(state["xp"])
        animate_victory(state["name"], xp_bonus)
    else:
        state["battles_lost"] = state.get("battles_lost", 0) + 1
        animate_defeat(npc_name)

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
    print(SPRITES.get(("chaos", "Baby"), ""))


def cmd_flex():
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    stage = get_stage(state["level"])
    primary = get_primary_brand(state.get("brand_xp", {}))
    _, brand_emoji = BRAND_COLORS.get(primary, ("white", "⚪"))
    faction = BRAND_FACTION.get(primary, "others")
    element = FACTION_ELEMENTS.get(faction, "chaos")
    elem_emoji = ELEMENT_EMOJI.get(element, "⚪")

    badges = " ".join(
        BRAND_COLORS.get(b, ("white", "⚪"))[1] for b in state.get("badges", [])
    )

    wins = state.get("battles_won", 0)
    losses = state.get("battles_lost", 0)
    total = wins + losses
    win_rate = f"{wins / total * 100:.0f}%" if total > 0 else "—"

    card = f"""
┌─────────────────────────────────┐
│  🦞 {state['name']}  {brand_emoji} {elem_emoji}  {element.upper():>13} │
│  Lv.{state['level']:<3} │ {stage:<9} │ {state['xp']:>7,} XP  │
│  ⚔ {wins}W/{losses}L ({win_rate})  │ {state['total_tokens_fed']:>9,} tok │
│  {badges:<31} │
│  Fed by {primary:<23} │
└─────────────────────────────────┘"""

    print(card)
    print()
    print("Copy and paste this to Discord / Twitter / anywhere!")


def cmd_challenge_export():
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    import base64

    stage = get_stage(state["level"])
    primary = get_primary_brand(state.get("brand_xp", {}))
    faction = BRAND_FACTION.get(primary, "others")
    element = FACTION_ELEMENTS.get(faction, "chaos")

    challenge_data = {
        "name": state["name"],
        "level": state["level"],
        "xp": state["xp"],
        "stage": stage,
        "element": element,
        "brand": primary,
        "hp_base": state.get("hp_base", 0),
        "atk_base": state.get("atk_base", 0),
        "def_base": state.get("def_base", 0),
        "spd_base": state.get("spd_base", 0),
        "battles_won": state.get("battles_won", 0),
    }

    encoded = base64.urlsafe_b64encode(
        json.dumps(challenge_data, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    print(f"🦞 CHALLENGE CODE:")
    print(f"   {encoded}")
    print()
    print(f"Send this to your opponent. They run:")
    print(f"   pet.py challenge-accept {encoded}")


def cmd_challenge_accept(code):
    state = load_state()
    if not state:
        print("No pet found. Run: pet.py init")
        return

    import base64

    # Decode opponent
    try:
        padding = 4 - len(code) % 4
        if padding != 4:
            code += "=" * padding
        opp = json.loads(base64.urlsafe_b64decode(code).decode())
    except Exception:
        print("❌ Invalid challenge code.")
        return

    player_level = state["level"]
    player_stage = get_stage(player_level)
    player_brand = state.get("primary_brand", "other") or "other"
    player_faction = BRAND_FACTION.get(player_brand, "others")
    player_element = FACTION_ELEMENTS.get(player_faction, "chaos")

    opp_level = opp["level"]
    opp_stage = opp.get("stage", get_stage(opp_level))
    opp_element = opp.get("element", "chaos")
    opp_name = opp.get("name", "Challenger")

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

    p_type_mod = TYPE_CHART.get((player_element, opp_element), 1.0)
    o_type_mod = TYPE_CHART.get((opp_element, player_element), 1.0)

    level_gap = abs(player_level - opp_level)
    p_atk_bonus = 1.3 if level_gap > 10 and player_level < opp_level else 1.0
    o_atk_bonus = 1.3 if level_gap > 10 and opp_level < player_level else 1.0

    element_skills = {
        "speed":     [{"name": "Blitz Strike",    "power": 1.0}, {"name": "Overdrive",      "power": 1.3}],
        "order":     [{"name": "Shield Bash",     "power": 1.0}, {"name": "Fortress Slam",  "power": 1.3}],
        "knowledge": [{"name": "Mind Pulse",      "power": 1.0}, {"name": "Data Cannon",    "power": 1.3}],
        "shadow":    [{"name": "Dark Claw",       "power": 1.0}, {"name": "Void Crush",     "power": 1.3}],
        "chaos":     [{"name": "Wild Slash",      "power": 1.0}, {"name": "Entropy Blast",  "power": 1.3}],
    }
    p_skills = element_skills.get(player_element, element_skills["chaos"])
    o_skills = element_skills.get(opp_element, element_skills["chaos"])

    p_elem_e = ELEMENT_EMOJI.get(player_element, "⚪")
    o_elem_e = ELEMENT_EMOJI.get(opp_element, "⚪")

    print(f"{'=' * 55}")
    print(f"  🦞 {state['name']} (Lv.{player_level} {p_elem_e})  VS  🦞 {opp_name} (Lv.{opp_level} {o_elem_e})")
    print(f"{'=' * 55}")

    if p_type_mod > 1.0:
        print(f"  {p_elem_e} > {o_elem_e} Type advantage! (x{p_type_mod})")
    elif o_type_mod > 1.0:
        print(f"  {o_elem_e} > {p_elem_e} Type disadvantage! (x{o_type_mod})")

    print(f"  Stage: {player_stage} vs {opp_stage}")
    print()

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
            crit = 1.5 if random.random() < 0.10 else 1.0
            variance = random.uniform(0.85, 1.15)
            return max(1, int(base * variance * crit)), crit > 1.0

        if p_first:
            order = [
                ("player", p_skill, p_stats, o_stats, p_atk_bonus, p_type_mod),
                ("opp", o_skill, o_stats, p_stats, o_atk_bonus, o_type_mod),
            ]
        else:
            order = [
                ("opp", o_skill, o_stats, p_stats, o_atk_bonus, o_type_mod),
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
                line = f"  R{turn}: 🦞 {skill['name']} → {dmg} dmg{crit_text} ({opp_name} HP: {o_hp})"
            else:
                p_hp -= dmg
                p_hp = max(0, p_hp)
                line = f"  R{turn}: 🦞 {skill['name']} → {dmg} dmg{crit_text} (You HP: {p_hp})"

            print(line)
            battle_log.append(line)

    print()

    won = p_hp > o_hp
    if won:
        xp_bonus = 50 + opp_level * 2
        state["battles_won"] = state.get("battles_won", 0) + 1
        state["xp"] += xp_bonus
        state["level"] = calc_level(state["xp"])
        print(f"  🏆 VICTORY over {opp_name}! +{xp_bonus} XP")
    else:
        state["battles_lost"] = state.get("battles_lost", 0) + 1
        print(f"  💀 DEFEATED by {opp_name}")

    save_state(state)

    # Save battle record
    battles = load_battles()
    battles.append({
        "opponent": opp_name,
        "opponent_level": opp_level,
        "opponent_element": opp_element,
        "player_level": player_level,
        "player_element": player_element,
        "pvp": True,
        "won": won,
        "timestamp": datetime.now().isoformat(),
        "log": battle_log,
    })
    battles = battles[-50:]
    save_battles(battles)

    print(f"  Record: {state['battles_won']}W / {state['battles_lost']}L")

    # Generate result card for sharing
    result_emoji = "🏆" if won else "💀"
    print(f"""
┌─────────────────────────────────────────┐
│  {result_emoji} PVP BATTLE RESULT                    │
│  🦞 {state['name']} (Lv.{player_level} {p_elem_e}) vs 🦞 {opp_name} (Lv.{opp_level} {o_elem_e})  │
│  Winner: {'YOU!' if won else opp_name:<20}            │
│  Rounds: {min(turn, 20):<3}                              │
└─────────────────────────────────────────┘""")


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
        print("  flex              Generate shareable card")
        print("  challenge-export  Create PvP challenge code")
        print("  challenge-accept  Accept a PvP challenge")
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

    elif cmd == "flex":
        cmd_flex()

    elif cmd == "challenge-export":
        cmd_challenge_export()

    elif cmd == "challenge-accept":
        if len(sys.argv) < 3:
            print("Usage: pet.py challenge-accept <CODE>")
            return
        cmd_challenge_accept(sys.argv[2])

    elif cmd == "rebirth":
        cmd_rebirth()

    else:
        print(f"Unknown command: {cmd}")
        print("Run: pet.py (no args) for help")


if __name__ == "__main__":
    main()
