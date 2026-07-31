# sims4-body-image-system
A The Sims 4 gameplay mod adding body-image goals, self-perception, and emotional reactions to body changes.

## Current status

This repository contains a testable vertical slice of the MVP:

- complete 30-cell resolver/threshold logic in `src/bodyimagesystem/domain.py`
  and `src/bodyimagesystem/resolver.py`, producing 50 stable symbolic buff keys;
- an integrated, persistent three-day stagnation cycle in
  `src/bodyimagesystem/stagnation.py` and `src/bodyimagesystem/tracking.py`;
- daily Fat/Fit snapshot sampling with a safe first-run baseline;
- isolated Sims 4 API access in `startup.py` and `sims_api.py`;
- all tuning IDs centralized in `src/bodyimagesystem/tuning.py`;
- a `.ts4script` build helper in `tools/build_ts4script.py`;
- unit and integration tests in `tests/`;
- a working English/Russian `trait_BIS_AppearanceFocused` resource in
  `s4s/BodyImageSystem.package`, wired to the script by its Instance ID.
- four hidden Teen–Elder body-goal traits in `s4s/BodyImageSystem.package`,
  all wired to the script by their Instance IDs.
- persistent self-esteem, Fat/Fit snapshot, stagnation, and goal-notification
  statistics;
- localized progress and stagnation test buffs.

All tuning IDs required by this vertical slice are populated in
`src/bodyimagesystem/tuning.py`. The next milestone is a controlled in-game
test of the startup hook, daily alarm, statistic access, and buff application.

## Vertical-slice resources

Implemented in `s4s/BodyImageSystem.package`:

- `statistic_BIS_SelfEsteem`
- `statistic_BIS_FatSnapshot` with default value `-999`
- `statistic_BIS_FitSnapshot` with default value `-999`
- `statistic_BIS_StagnationDays` with default value `0`
- `buff_BIS_Test_Progress`
- `buff_BIS_Stagnation`
- four hidden `trait_BIS_Goal_*` traits
- visible `trait_BIS_AppearanceFocused`

Verified EA reference exports for `commodity_Fitness_Fat` and
`commodity_Fitness_Fit` live under `s4s/references/`. They are not included in
the mod package, so the mod does not override EA tuning.

## Local checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Build

Use Python 3.7 for a real Sims 4 artifact:

```bash
python3.7 tools/build_ts4script.py
```

For a local smoke test of the build script only:

```bash
python3 tools/build_ts4script.py --skip-version-check
```

The output is written to `dist/BodyImageSystem.ts4script`.

The generated script is ready for the first controlled in-game vertical-slice
test, but the mod is not feature-complete and does not yet provide mirror goal
selection interactions.

## Temporary in-game debug commands

The script currently registers three temporary commands for the active Sim:

```text
bis.goal lose_weight
bis.goal gain_weight
bis.goal gain_muscle
bis.goal maintain
bis.goal none
bis.sample
bis.status
```

`bis.goal` replaces the active hidden goal trait and resets the stagnation and
goal-achievement counters. `bis.sample` immediately invokes the same sampling
function as the daily alarm. Its first run only creates snapshots when a
baseline does not exist; later runs process pending Fat/Fit changes. Every
manual run counts as a sampling window for stagnation, even if no in-game day
has passed. `bis.status` prints the goal, appearance-focused trait, body values,
snapshots, pending deltas, self-esteem, and progress counters.

These use `CommandType.Live`, so `testingcheats true` is not required. Remove
the debug-command installation from `startup.py` before a public release.
