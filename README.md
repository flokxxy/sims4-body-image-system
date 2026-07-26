# sims4-body-image-system
A The Sims 4 gameplay mod adding body-image goals, self-perception, and emotional reactions to body changes.

## Current status

This repository contains the first script-side scaffold for the MVP:

- complete 30-cell resolver/threshold logic in `src/bodyimagesystem/domain.py`
  and `src/bodyimagesystem/resolver.py`, producing 50 stable symbolic buff keys;
- a pure, repeatable three-day stagnation state machine in
  `src/bodyimagesystem/stagnation.py`;
- Sims 4 integration placeholders in `src/bodyimagesystem/startup.py`, `tracking.py`, and `sims_api.py`;
- all tuning IDs centralized in `src/bodyimagesystem/tuning.py`;
- a `.ts4script` build helper in `tools/build_ts4script.py`;
- unit tests for the pure logic in `tests/`.
- a working English/Russian `trait_BIS_AppearanceFocused` resource in
  `s4s/BodyImageSystem.package`, wired to the script by its Instance ID.

Before in-game testing, create the required `.package` resources in Sims 4 Studio
and replace the remaining placeholder `0x0000000000000000` values in
`src/bodyimagesystem/tuning.py`.

## MVP resource checklist

Create these first:

- `statistic_BIS_SelfEsteem`
- `statistic_BIS_FatSnapshot` with default value `-999`
- `statistic_BIS_FitSnapshot` with default value `-999`
- `trait_BIS_Goal_LoseWeight`
- `buff_BIS_Test_Progress`

Also verify the built-in resource IDs for `commodity_Fat` and `commodity_Fit`
against the current decompiled game tuning.

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

The generated script is not ready for in-game use until the remaining resources
have real instance IDs in `src/bodyimagesystem/tuning.py`.
