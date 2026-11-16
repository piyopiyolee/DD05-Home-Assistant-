# Local hassio-ftms 0.24.6 modifications (as deployed 2026-11-16)

These are **only the modified files** from [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6, plus a new local module. They are **not** a complete integration — install hassio-ftms 0.24.6 first, then copy these three files into `/config/custom_components/ftms/` and restart Home Assistant.

hassio-ftms is Apache License 2.0; see `../../../patches/LICENSE-hassio-ftms-Apache-2.0`. Per Apache-2.0 §4(b), `__init__.py` and `sensor.py` carry comments describing the changes.

| File | What changed (2026-11-16, Asia/Taipei) |
|---|---|
| `__init__.py` | Existing 2026-11-14 lenient Training Status monkey-patch, plus raw-byte debug log; `CONTROL_TIMEOUT = 8.0` passed to `pyftms.get_client(...)`; imports `updater_patch`. |
| `sensor.py` | Enum sensors (`training_status`, `movement_direction`) keep `native_value = None` when the value is missing or not in `options`, instead of falling back to `0` (which raised `ValueError`). |
| `updater_patch.py` | **New file.** Patches pyftms 0.4.10 `DataUpdater._on_notify` so alternating Treadmill Data packets (with/without `step_count`) are not dropped with `KeyError`. Must sit next to `__init__.py`. |

Full narrative, test times, backups and the open segment-boundary speed bug: [`docs/2026-11-16-dd05-debug-log.md`](../../../docs/2026-11-16-dd05-debug-log.md).
