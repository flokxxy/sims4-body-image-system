"""Tuning instance IDs used by the script side.

Replace the placeholder values after creating resources in Sims 4 Studio.
Keeping every tuning reference in one module makes the ID handoff explicit.
"""

# Built-in game statistic instance IDs. Verify in decompiled tuning before use.
COMMODITY_FAT = 0x0000000000000000
COMMODITY_FIT = 0x0000000000000000

# Custom statistics.
STATISTIC_SELF_ESTEEM = 0x0000000000000000
STATISTIC_FAT_SNAPSHOT = 0x0000000000000000
STATISTIC_FIT_SNAPSHOT = 0x0000000000000000
STATISTIC_STAGNATION_DAYS = 0x0000000000000000
STATISTIC_GOAL_ACHIEVED_FLAG = 0x0000000000000000

# Custom traits.
# Hash source and localization keys are documented in docs/RESOURCE_IDS.md.
TRAIT_APPEARANCE_FOCUSED = 0xA8F4EDC9F71B05B9
TRAIT_GOAL_LOSE_WEIGHT = 0x0000000000000000
TRAIT_GOAL_GAIN_WEIGHT = 0x0000000000000000
TRAIT_GOAL_GAIN_MUSCLE = 0x0000000000000000
TRAIT_GOAL_MAINTAIN = 0x0000000000000000

# MVP buff: create this first, then expand to the full resolver catalog.
BUFF_TEST_PROGRESS = 0x0000000000000000

# Populate this mapping as the final buff resources are authored. During the
# vertical-slice MVP, every PROGRESS key may fall back to BUFF_TEST_PROGRESS.
REACTION_BUFF_IDS = {}


def reaction_buff_id(buff_key):
    """Resolve a symbolic resolver key to a tuned buff instance ID."""
    buff_id = REACTION_BUFF_IDS.get(buff_key)
    if buff_id is not None:
        return buff_id
    if buff_key and buff_key.startswith("progress."):
        return BUFF_TEST_PROGRESS
    return 0
