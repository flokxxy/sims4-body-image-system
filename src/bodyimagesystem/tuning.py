"""Verified tuning instance IDs used by the script-side vertical slice.

Keeping every tuning reference in one module makes the handoff from the package
and EA reference exports explicit and auditable.
"""

# Built-in game statistic instance IDs. Reference exports live in
# s4s/references/ and must not be included in the mod package as overrides.
COMMODITY_FAT = 0x00000000000040CD
COMMODITY_FIT = 0x00000000000040CE

# Custom statistics.
STATISTIC_SELF_ESTEEM = 0x00000000CDE0665B
STATISTIC_FAT_SNAPSHOT = 0x00000000AE7D61F7
STATISTIC_FIT_SNAPSHOT = 0x000000008926D7AF
STATISTIC_STAGNATION_DAYS = 0x00000000CE0CDD56
STATISTIC_GOAL_ACHIEVED_FLAG = 0x00000000C06C893C

# Custom traits.
# Hash source and localization keys are documented in docs/RESOURCE_IDS.md.
TRAIT_APPEARANCE_FOCUSED = 0x00000000D4BB0699
TRAIT_GOAL_LOSE_WEIGHT = 0x0000000080A37607
TRAIT_GOAL_GAIN_WEIGHT = 0x00000000E82B728D
TRAIT_GOAL_GAIN_MUSCLE = 0x00000000C37BC038
TRAIT_GOAL_MAINTAIN = 0x00000000C1D975C3

# MVP buffs. The full resolver catalog will replace the shared progress buff.
BUFF_TEST_PROGRESS = 0x00000000C0F3A961
BUFF_STAGNATION = 0x00000000EE3B5EF1

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
