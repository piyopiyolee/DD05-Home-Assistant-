# BGYM DD05 Walking Pad × Home Assistant

Control and monitor a **BGYM DD05** walking treadmill from Home Assistant over Bluetooth (FTMS), with a phone remote-control dashboard, a structured interval-training runner, Assist (zh-TW) voice commands and optional Google Assistant / Google Home control.

> 中文說明請見 [README.zh-TW.md](README.zh-TW.md)

> ⚠️ **Read the [Safety](#safety) section before using any of this.** A treadmill can injure you. Nothing here starts the belt on its own, and you must always be standing on the machine with the safety key clipped on.

## What it does

- **Live data**: speed, incline, elapsed time, distance, energy, heart rate.
- **Remote dashboard** (`dashboards/treadmill_remote.yaml`): start/pause, speed ±0.5 km/h, incline ±1 %, stop.
- **Training runner** (`homeassistant/packages/dd05_training.yaml` + `dashboards/training.yaml`): a generic, timestamp-based segment runner (with differential writes and readback verification), plus *Interval 10 min* (with an SVG schedule chart) and a 13-slider *Custom* program. New programs are added by writing a new definition script only.
- **Voice**: Assist custom sentences in Traditional Chinese (開始走 / 暫停走 / 停止走 / 加速度 / 減速度 / 加坡度 / 減坡度, plus starting *Interval 10 min*, pausing, resuming, and ending training), and the same scripts exposed to Google Assistant as scenes.

## Tested setup

| Item | Version / value |
|---|---|
| Treadmill | BGYM DD05 (reports as **FitShow FS-BT-F5**, firmware `V1.0.5beta`, hardware `V1.0.0`) |
| BLE service | Fitness Machine Service (FTMS, UUID `0x1826`) |
| Range exposed in HA | speed 1.0–6.0 km/h (step 0.1), incline 0–15 % (step 1) |
| Home Assistant | 2026.10.4 (Docker) |
| Integration | [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6 (pyftms 0.4.10) + the patch in `patches/` |
| Bluetooth proxy | ESP32-C3 (esp32-c3-devkitm-1), ESPHome 2026.10.1, **ESP-IDF pinned to 5.5.5** |

Other FitShow-based walking pads that speak FTMS will probably work too, but only the DD05 has been tested.

## Architecture

```
BGYM DD05 (FitShow FS-BT-F5, FTMS 0x1826)
        │  Bluetooth LE (active connection)
        ▼
ESP32-C3 ESPHome Bluetooth proxy   (esphome/bt-proxy-esp32c3.yaml)
        │  Wi-Fi, ESPHome native API
        ▼
Home Assistant ── hassio-ftms (custom integration, patched)
        ├── entities: sensor.treadmill_*, number.treadmill_*, button.treadmill_*
        ├── packages/dd05_treadmill_remote.yaml  → remote scripts
        ├── packages/dd05_training.yaml          → helpers, runner, safety watchdog
        ├── dashboards (Treadmill remote, Training)
        ├── Assist custom sentences + intent_script
        └── Google Assistant (scripts exposed as scenes)
```

## Repository layout

```
esphome/                       ESP32-C3 BT proxy config + secrets example
homeassistant/packages/        HA packages (scripts, helpers, automations)
homeassistant/www/training/    Static assets (Interval 10 min SVG chart)
homeassistant/custom_sentences/zh-TW/   Assist sentences
homeassistant/configuration-snippets/   intent_script, google_assistant, packages include
dashboards/                    Lovelace dashboards (paste into Raw configuration editor)
homeassistant/custom_components/ftms/  modified hassio-ftms files (not a complete integration)
patches/                       hassio-ftms patch (Apache-2.0, see patches/README.md)
docs/                          architecture notes, upstream notes, dated debug logs
```

## Installation

### 1. Bluetooth proxy (ESP32-C3 + ESPHome)

1. Copy `esphome/secrets.yaml.example` to `esphome/secrets.yaml` and fill it in.
2. Flash `esphome/bt-proxy-esp32c3.yaml` (first time over USB, later OTA).
3. Place the proxy close to the treadmill (same room). Home Assistant will discover it through the ESPHome integration.

**Why ESP-IDF 5.5.5?** With ESPHome 2026.10.1 the default framework was ESP-IDF 5.5.6. On that build the proxy connected to the DD05 but GATT service discovery ended early, so the FTMS service `0x1826` was never reported and the integration could not set up. Raising `CONFIG_BT_GATTC_MAX_CACHE_CHAR` did not help. Pinning `framework: version: 5.5.5` fixed it. ESPHome prints a "not the recommended version" warning; this is expected. Re-test whenever you upgrade ESPHome; a newer IDF may fix it, in which case you can drop the pin.

The author's proxies ran without API encryption or an OTA password; this example adds both as recommended hardening.

### 2. hassio-ftms integration + patch

1. Install [hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6 (HACS custom repository or manual copy to `/config/custom_components/ftms/`).
2. Apply the patch:
   ```bash
   cd /config
   patch -p1 < patches/hassio-ftms-0.24.6-lenient-training-status.patch
   ```
3. Copy the three files in `homeassistant/custom_components/ftms/` (`__init__.py`, `sensor.py`, `updater_patch.py`) over the corresponding paths under `/config/custom_components/ftms/`. `updater_patch.py` is new and must sit next to `__init__.py`. See `patches/README.md` and `homeassistant/custom_components/ftms/README.md`.
4. Restart Home Assistant. The DD05 should be discovered via Bluetooth (FTMS). Add it. All YAML here uses entity IDs `*.treadmill_*` (the default when the device is named "Treadmill"); if yours differ, rename the device or entities.

**What the patch does:** the DD05 sends *Training Status* notifications with flag bits that are undefined in the FTMS spec (e.g. `0x46`). pyftms 0.4.10 raises on them and the integration setup aborts. The patch keeps only the two spec-defined flag bits and, if a status still cannot be parsed, logs a warning and skips it instead of crashing. See `patches/README.md`. The proper long-term fix belongs upstream (pyftms / hassio-ftms); see `docs/upstream-notes.md`.

### 3. Home Assistant packages

1. Enable packages (once) using `homeassistant/configuration-snippets/homeassistant_packages.yaml`.
2. Copy `homeassistant/packages/*.yaml` to `/config/packages/`.
3. In `dd05_training.yaml`, replace `notify.mobile_app_YOUR_PHONE` with your phone's notify service (or delete that step).
4. Check configuration, then restart.
5. *(First deploy)* `input_number.training_custom_*` helpers intentionally omit `initial:` so reloads and restarts preserve your slider settings; optionally call `input_number.set_value` once to populate recommended defaults (15 rounds, warm-up 60 s / 3.0 / 0 %, fast 60 s / 4.5 / 4 %, rest 45 s / 3.0 / 0 %, cool-down 60 s / 2.0 / 0 %; total `28:15`).

### 4. Dashboards

1. Copy `homeassistant/www/training/interval10_v2.svg` to `/config/www/training/interval10_v2.svg` (restart HA once if `/config/www/` did not previously exist so `/local/training/interval10_v2.svg` is served).
2. Settings → Dashboards → Add dashboard (e.g. "Treadmill", icon `mdi:walk`, and "Training", icon `mdi:run`). Open each one → ⋮ → Edit → Raw configuration editor, and paste `dashboards/treadmill_remote.yaml` / `dashboards/training.yaml`. Only built-in cards are used (`picture` card renders the SVG chart).

### 5. Voice commands

- **Assist (zh-TW):** copy `homeassistant/custom_sentences/zh-TW/*.yaml` to `/config/custom_sentences/zh-TW/`, merge `configuration-snippets/intent_script.yaml` into `configuration.yaml`, restart.
- **Google Assistant (manual YAML setup):** merge `configuration-snippets/google_assistant.yaml` into your existing `google_assistant:` block, restart, then call `google_assistant.request_sync`. Scripts show up in Google Home as scenes.

| Say | Action |
|---|---|
| 開始走 / 走步機開始 | start / resume |
| 暫停走 / 走步機暫停 | pause |
| 停止走 / 走步機停止 | stop |
| 加速度 / 減速度 | speed +/- 0.5 km/h (only while the belt is moving) |
| 加坡度 / 減坡度 | incline +/- 1 % |
| 開始間歇訓練 / 訓練暫停 / 繼續訓練 / 結束訓練 | training runner start / pause-resume / end |

## Training runner

- **Helpers**: `input_select.training_state` (`idle/starting/running/paused/resuming/finishing`, `initial: idle`), timestamps, current phase, round, last target.
- **`script.training_run`**: generic runner that takes `program_name` and a list of `segments` (`{name, round, dur, s0, i0, s1?, i1?, ramp_dur?, step?}`), computes elapsed time from timestamps (no drift), uses differential writes with a 0.5 s speed-to-incline gap, and verifies treadmill readback after 1.5 s (up to 4 attempts) so DD05 firmware doesn't drop or overwrite segment transitions.
- **`script.training_interval_10`**: the *Interval 10 min* program: 45 s warm-up (3.0 km/h / 0 %), 5 rounds × (60 s fast 4.5 km/h / 4 % + 45 s recovery 3.0 km/h / 0 %), 30 s cool-down (2.0 km/h / 0 %); total 600 s (10:00), visualized by `/local/training/interval10_v2.svg`.
- **`script.training_custom`**: *Custom* program reading a snapshot of 13 `input_number.training_custom_*` sliders (rounds 5–30, per-phase duration 30–120 s, speed 2.0–6.0 km/h, incline 0–15 %; recommended defaults give 15 rounds / `28:15` via `sensor.training_custom_total_mmss`).
- **`script.training_pause` / `script.training_end`**: pause ↔ resume toggle (re-applies target speed/incline on resume), and abort + stop.
- **Watchdog automations**: while running, if speed < 0.1 km/h for 3 s (stop button, safety key pulled), the sensor is unavailable for 10 s, or `script.training_run` exits unexpectedly (`automation.training_run_died_guard`), the program is cleaned up/aborted and you get a notification.
- To add a program: copy `training_interval_10`, change `program_name` and `segments`, and add a button + subview to the Training dashboard. The runner does not change.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Device never appears / connection fails | The FitShow phone app (or another phone) is holding the BLE connection. The DD05 accepts only one central. Close the app / turn off Bluetooth on the phone. |
| Proxy connects but setup fails, FTMS service missing | GATT service discovery cut off (only the first standard services, e.g. Device Information `0x180A`, are seen). Use ESP-IDF 5.5.5 as in `esphome/bt-proxy-esp32c3.yaml`; after reflashing, clear the proxy's GATT cache for the treadmill or power-cycle both. |
| Setup aborts with a Training Status parse error | Apply the patch in `patches/`. |
| Log: `Skipping unparsable FTMS training status …` | Expected with the patch; the DD05 sends a non-standard status (e.g. code 83 with a text payload). Harmless. |
| `sensor.treadmill_status` unavailable | Known: caused by the same non-standard training status. Speed/incline/controls are unaffected. Not fixed yet. |
| Belt does not start immediately | FitShow belts count down a few seconds after start; the runner waits up to 30 s for speed > 0. |
| Speed buttons do nothing when stopped | By design: speed is only changed while the belt is moving. |
| Proxy far from the treadmill → drops | Put a proxy in the same room; walls noticeably hurt the connection. |

## Safety

- **Always clip the safety key to your clothing.** Pulling it must stop the belt; the watchdog then aborts any running program.
- **Only use remote/voice/program control while you are standing on the treadmill.** Never start it for someone else or for an empty machine.
- **Programs never auto-start.** There are no schedules or automations that start the belt or a program; the training automations only stop/abort.
- Speed/incline are never written while the belt is stopped, and values are clamped to 1.0–6.0 km/h and 0–15 %.
- After a Home Assistant restart the runner resets to `idle`.
- Keep children and pets away. Test new programs at low speed first.

## Development log

- **2026-11-16**: Tests and fixes (timeouts, training runner, display dropouts), plus the segment-boundary speed overwrite bug discovered in initial live testing — see [docs/2026-11-16-dd05-debug-log.md](docs/2026-11-16-dd05-debug-log.md) (Traditional Chinese, times in Asia/Taipei).
- **2026-11-17**: Root-cause evidence & fix for the segment-boundary bug (verified in live testing), *Interval 10 min* v2 + SVG chart, 13-slider *Custom* program, and voice switch from 35 min to *Interval 10 min* — see [docs/2026-11-17-dd05-training-update.md](docs/2026-11-17-dd05-training-update.md) (Traditional Chinese, times in Asia/Taipei).

## Disclaimer

This is an unofficial community project. It is **not affiliated with, endorsed by, or supported by BGYM, FitShow, or Home Assistant / Nabu Casa**. All trademarks belong to their owners. Use at your own risk; you are responsible for safe operation of your equipment. Remote control of exercise equipment can cause injury. Modifying integrations may break on updates.

## License

See [LICENSE](LICENSE) for this project's own files. The file in `patches/` modifies hassio-ftms, which is licensed under Apache-2.0 (`patches/LICENSE-hassio-ftms-Apache-2.0`).

## Credits

- [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) and pyftms by Sergey Dudanov.
- ESPHome Bluetooth proxy.
