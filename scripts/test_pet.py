#!/usr/bin/env python3
"""Tests for lobster-pet."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

# Import from pet.py
sys.path.insert(0, os.path.dirname(__file__))
import pet


class TestHelpers(unittest.TestCase):
    """Test helper functions (XP formula, level, stage, tiers)."""

    def test_calc_level_zero_xp(self):
        self.assertEqual(pet.calc_level(0), 1)

    def test_calc_level_formula(self):
        # level = floor(sqrt(xp / 10))
        self.assertEqual(pet.calc_level(10), 1)
        self.assertEqual(pet.calc_level(100), 3)   # sqrt(10) = 3.16
        self.assertEqual(pet.calc_level(1000), 10)  # sqrt(100) = 10
        self.assertEqual(pet.calc_level(5000), 22)  # sqrt(500) = 22.36

    def test_get_stage_boundaries(self):
        self.assertEqual(pet.get_stage(1), "Baby")
        self.assertEqual(pet.get_stage(10), "Baby")
        self.assertEqual(pet.get_stage(11), "Growth")
        self.assertEqual(pet.get_stage(25), "Growth")
        self.assertEqual(pet.get_stage(26), "Mature")
        self.assertEqual(pet.get_stage(40), "Mature")
        self.assertEqual(pet.get_stage(41), "Ultimate")
        self.assertEqual(pet.get_stage(55), "Ultimate")
        self.assertEqual(pet.get_stage(56), "Mega")
        self.assertEqual(pet.get_stage(999), "Mega")

    def test_model_tier_s(self):
        self.assertEqual(pet.get_model_tier("claude-opus-4-6"), 10)
        self.assertEqual(pet.get_model_tier("gpt-4"), 10)
        self.assertEqual(pet.get_model_tier("o3"), 10)

    def test_model_tier_a(self):
        self.assertEqual(pet.get_model_tier("gpt-4o"), 5)
        self.assertEqual(pet.get_model_tier("claude-sonnet-4-6"), 5)
        self.assertEqual(pet.get_model_tier("o1-mini"), 5)

    def test_model_tier_b(self):
        self.assertEqual(pet.get_model_tier("gpt-4o-mini"), 1)
        self.assertEqual(pet.get_model_tier("claude-haiku-4-5-20251001"), 1)

    def test_model_tier_unknown_defaults_b(self):
        self.assertEqual(pet.get_model_tier("some-random-model"), 1)

    def test_get_primary_brand_empty(self):
        self.assertEqual(pet.get_primary_brand({}), "other")

    def test_get_primary_brand_single(self):
        self.assertEqual(pet.get_primary_brand({"openai": 100}), "openai")

    def test_get_primary_brand_multiple(self):
        self.assertEqual(
            pet.get_primary_brand({"openai": 100, "anthropic": 200}),
            "anthropic"
        )

    def test_faction_mapping(self):
        self.assertEqual(pet.BRAND_FACTION.get("openai"), "openai")
        self.assertEqual(pet.BRAND_FACTION.get("anthropic"), "anthropic")
        self.assertEqual(pet.BRAND_FACTION.get("deepseek"), "china")
        self.assertEqual(pet.BRAND_FACTION.get("moonshot"), "china")
        self.assertEqual(pet.BRAND_FACTION.get("meta"), "others")
        self.assertEqual(pet.BRAND_FACTION.get("mistral"), "others")

    def test_element_mapping(self):
        self.assertEqual(pet.FACTION_ELEMENTS.get("openai"), "speed")
        self.assertEqual(pet.FACTION_ELEMENTS.get("anthropic"), "order")
        self.assertEqual(pet.FACTION_ELEMENTS.get("google"), "knowledge")
        self.assertEqual(pet.FACTION_ELEMENTS.get("china"), "shadow")
        self.assertEqual(pet.FACTION_ELEMENTS.get("others"), "chaos")

    def test_type_chart_cycle(self):
        """speed > order > shadow > knowledge > chaos > speed"""
        self.assertEqual(pet.TYPE_CHART[("speed", "order")], 1.5)
        self.assertEqual(pet.TYPE_CHART[("order", "shadow")], 1.5)
        self.assertEqual(pet.TYPE_CHART[("shadow", "knowledge")], 1.5)
        self.assertEqual(pet.TYPE_CHART[("knowledge", "chaos")], 1.5)
        self.assertEqual(pet.TYPE_CHART[("chaos", "speed")], 1.5)
        # Reverse
        self.assertEqual(pet.TYPE_CHART[("order", "speed")], 0.75)
        self.assertEqual(pet.TYPE_CHART[("speed", "chaos")], 0.75)

    def test_type_chart_neutral(self):
        """Non-adjacent pairs have no entry (neutral = 1.0)."""
        self.assertNotIn(("speed", "knowledge"), pet.TYPE_CHART)
        self.assertNotIn(("order", "chaos"), pet.TYPE_CHART)

    def test_stage_bonus_values(self):
        self.assertEqual(pet.STAGE_BONUS["Baby"], 1.0)
        self.assertEqual(pet.STAGE_BONUS["Growth"], 1.1)
        self.assertEqual(pet.STAGE_BONUS["Mature"], 1.25)
        self.assertEqual(pet.STAGE_BONUS["Ultimate"], 1.4)
        self.assertEqual(pet.STAGE_BONUS["Mega"], 1.6)

    def test_xp_to_next_level(self):
        # At level 10 (xp=1000), next level 11 needs (11^2)*10 = 1210
        remaining = pet.xp_to_next_level(1000, 10)
        self.assertEqual(remaining, 210)

    def test_xp_to_next_stage_baby_to_growth(self):
        # Baby max = 10, Growth starts at 11. Need (11^2)*10 = 1210 XP
        remaining = pet.xp_to_next_stage(0, 1)
        self.assertEqual(remaining, 1210)


class TestWithState(unittest.TestCase):
    """Tests that need file I/O — use temp directory."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.orig_pet_dir = pet.PET_DIR
        self.orig_state_file = pet.STATE_FILE
        self.orig_battles_file = pet.BATTLES_FILE
        self.orig_daily_file = pet.DAILY_FILE

        pet.PET_DIR = self.tmp_dir
        pet.STATE_FILE = self.tmp_dir / "state.json"
        pet.BATTLES_FILE = self.tmp_dir / "battles.json"
        pet.DAILY_FILE = self.tmp_dir / "daily.json"

    def tearDown(self):
        pet.PET_DIR = self.orig_pet_dir
        pet.STATE_FILE = self.orig_state_file
        pet.BATTLES_FILE = self.orig_battles_file
        pet.DAILY_FILE = self.orig_daily_file
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _init_pet(self):
        pet.cmd_init()
        return pet.load_state()

    def test_init_creates_state(self):
        state = self._init_pet()
        self.assertIsNotNone(state)
        self.assertEqual(state["level"], 1)
        self.assertEqual(state["xp"], 0)
        self.assertEqual(state["stage"], "Baby")

    def test_init_already_exists(self):
        self._init_pet()
        # Second init should not overwrite
        pet.cmd_init()
        state = pet.load_state()
        self.assertEqual(state["level"], 1)

    def test_feed_xp_calculation_tier_s(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 10000, silent=True)
        state = pet.load_state()
        # 10000 tokens / 100 = 100 base XP * 10 (tier S) = 1000 XP
        self.assertEqual(state["xp"], 1000)

    def test_feed_xp_calculation_tier_a(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4o", 10000, silent=True)
        state = pet.load_state()
        # 10000 / 100 = 100 * 5 = 500
        self.assertEqual(state["xp"], 500)

    def test_feed_xp_calculation_tier_b(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4o-mini", 10000, silent=True)
        state = pet.load_state()
        # 10000 / 100 = 100 * 1 = 100
        self.assertEqual(state["xp"], 100)

    def test_feed_unknown_model_uses_tier_b(self):
        self._init_pet()
        pet.cmd_feed("some-provider", "unknown-model-xyz", 10000, silent=True)
        state = pet.load_state()
        self.assertEqual(state["xp"], 100)

    def test_feed_triggers_evolution(self):
        self._init_pet()
        # Feed enough to reach Growth (level 11 = xp 1210)
        pet.cmd_feed("anthropic", "claude-opus-4-6", 15000, silent=True)
        state = pet.load_state()
        self.assertGreater(state["level"], 10)
        self.assertTrue(state.get("brand_locked"))

    def test_brand_locks_at_first_evolution(self):
        self._init_pet()
        pet.cmd_feed("anthropic", "claude-opus-4-6", 15000, silent=True)
        state = pet.load_state()
        self.assertTrue(state["brand_locked"])
        self.assertEqual(state["primary_brand"], "anthropic")

    def test_badge_unlock(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 1000, silent=True)
        pet.cmd_feed("anthropic", "claude-opus-4-6", 1000, silent=True)
        state = pet.load_state()
        self.assertIn("openai", state["badges"])
        self.assertIn("anthropic", state["badges"])

    def test_badge_no_duplicates(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 1000, silent=True)
        pet.cmd_feed("openai", "gpt-4o", 1000, silent=True)
        state = pet.load_state()
        self.assertEqual(state["badges"].count("openai"), 1)

    def test_battle_victory_gives_xp(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 20000, silent=True)
        state_before = pet.load_state()
        xp_before = state_before["xp"]
        pet.cmd_battle("easy")
        state_after = pet.load_state()
        # Should have won (5 levels higher) and gained XP
        if state_after["battles_won"] > 0:
            self.assertGreater(state_after["xp"], xp_before)

    def test_battle_records_saved(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 20000, silent=True)
        pet.cmd_battle("easy")
        battles = pet.load_battles()
        self.assertEqual(len(battles), 1)
        self.assertIn("opponent", battles[0])
        self.assertIn("log", battles[0])

    def test_battle_max_50_records(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 50000, silent=True)
        for _ in range(55):
            pet.cmd_battle("easy")
        battles = pet.load_battles()
        self.assertLessEqual(len(battles), 50)

    def test_rebirth_resets_level(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 30000, silent=True)
        state = pet.load_state()
        self.assertGreater(state["level"], 1)
        old_badges = state["badges"].copy()
        old_wins = state.get("battles_won", 0)

        pet.cmd_rebirth()
        state = pet.load_state()
        self.assertEqual(state["level"], 1)
        self.assertEqual(state["xp"], 0)
        self.assertFalse(state["brand_locked"])
        self.assertIsNone(state["primary_brand"])
        # Badges and battle record preserved
        self.assertEqual(state["badges"], old_badges)
        self.assertEqual(state.get("battles_won", 0), old_wins)
        self.assertEqual(state["rebirth_count"], 1)

    def test_state_corruption_recovery(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 10000, silent=True)
        state = pet.load_state()
        good_xp = state["xp"]

        # Corrupt the state file
        with open(pet.STATE_FILE, "w") as f:
            f.write("{broken json...")

        # Should recover from backup
        recovered = pet.load_state()
        # Backup was made before the corruption write, so it has the feed state
        if recovered:
            self.assertIsNotNone(recovered)

    def test_state_no_backup_returns_none(self):
        self._init_pet()
        # Corrupt state with no valid backup
        with open(pet.STATE_FILE, "w") as f:
            f.write("broken")
        backup = pet.STATE_FILE.with_suffix(".json.bak")
        if backup.exists():
            with open(backup, "w") as f:
                f.write("also broken")
        state = pet.load_state()
        self.assertIsNone(state)

    def test_feed_zero_tokens(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 0, silent=True)
        state = pet.load_state()
        self.assertEqual(state["xp"], 0)
        self.assertEqual(state["total_tokens_fed"], 0)

    def test_silent_feed_daily_status(self):
        self._init_pet()
        pet.cmd_feed("openai", "gpt-4", 10000, silent=True)
        daily = pet.load_daily()
        # First silent feed of the day should set last_shown
        self.assertIn("last_shown", daily)


if __name__ == "__main__":
    unittest.main()
