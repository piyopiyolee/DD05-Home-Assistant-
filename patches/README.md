# hassio-ftms patch: lenient Training Status parsing

`hassio-ftms-0.24.6-lenient-training-status.patch` applies to
[dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) **0.24.6**
(`custom_components/ftms/__init__.py`, pyftms 0.4.10).

## Problem
The BGYM DD05 (FitShow FS-BT-F5, firmware V1.0.5beta) sends FTMS *Training Status*
(characteristic 0x2AD3) notifications whose flags byte has bits set that the FTMS
specification does not define (e.g. `0x46`). pyftms raises while parsing them and
the integration fails to set up. Some notifications also carry a status code that
is not in the spec (seen: `83` with a text payload).

## Fix
Wraps `MachineController._on_training_status` so that:
1. only the two spec-defined flag bits are kept (`flags &= 0x03`);
2. any remaining parse error is logged as a warning and the notification skipped.

Speed, incline, controls and all other data keep working. Known side effect:
`sensor.treadmill_status` can stay unavailable on this treadmill.

## Apply / revert
```bash
cd /config
patch -p1 --dry-run < patches/hassio-ftms-0.24.6-lenient-training-status.patch
patch -p1 < patches/hassio-ftms-0.24.6-lenient-training-status.patch
# revert:
patch -p1 -R < patches/hassio-ftms-0.24.6-lenient-training-status.patch
```
Restart Home Assistant afterwards. Updating hassio-ftms via HACS overwrites the patch.

## License
This patch is a modification of hassio-ftms and is provided under the
**Apache License 2.0** (see `LICENSE-hassio-ftms-Apache-2.0`). Per Apache-2.0 §4(b),
the modified file carries a comment stating it was changed.

## Upstream
This is a monkey-patch workaround. The clean fix is in pyftms' Training Status
parser (mask reserved flag bits, tolerate unknown status codes). See
`../docs/upstream-notes.md` for a draft issue / PR description.


---

## Later local modifications (2026-11-16)

The 2026-11-14 Training Status patch above is still in effect. On 2026-11-16
additional changes were applied to the *already patched* integration, and are
kept as the current files in `../homeassistant/custom_components/ftms/`
(not as a second `.patch` file). Copy those three files over a stock
hassio-ftms 0.24.6 tree after applying the 2026-11-14 patch (or copy them
over the already-patched tree):

1. `CONTROL_TIMEOUT = 8.0` on `pyftms.get_client` (default 2 s was too short
   for this treadmill).
2. Raw Training Status bytes logged at DEBUG before the flags mask.
   The first read on this DD05 is `02 53 2D 55 70 64 61 74 65 5F 31 2E 30`
   (`S-Update_1.0`), not a standard status notification.
3. ENUM sensors no longer fall back to `0` when the value is missing.
4. New `updater_patch.py`: pyftms 0.4.10 `DataUpdater._on_notify` dropped
   Treadmill Data notifications with `KeyError: 'step_count'` when the device
   alternates packets with and without that field.

Full test log (Traditional Chinese, Asia/Taipei times) and the open
segment-boundary speed bug: `../docs/2026-11-16-dd05-debug-log.md`.
