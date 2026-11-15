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
