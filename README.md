# BGYM DD05 Walking Pad × Home Assistant

Control and monitor a **BGYM DD05** walking treadmill from Home Assistant over Bluetooth (FTMS), with a phone remote-control dashboard, a structured interval-training runner, Assist (zh-TW) voice commands and optional Google Assistant / Google Home control.

> 中文說明請見 [README.zh-TW.md](README.zh-TW.md)

> ⚠️ **Read the [Safety](#safety) section before using any of this.** A treadmill can injure you. Nothing here starts the belt on its own, and you must always be standing on the machine with the safety key clipped on.

## What it does

- **Live data**: speed, incline, elapsed time, distance, energy, heart rate.
- **Remote dashboard** (`dashboards/treadmill_remote.yaml`, requires the HACS [button-card](https://github.com/custom-cards/button-card) custom card): the main view has speed ±0.5 km/h, incline ±1 %, time and distance, start/pause/stop, and an HIIT toggle that decides whether Start runs a program or just starts the belt manually. The settings subview uses +/- steppers for warm-up, fast walk, recovery, cool-down and rounds. Screenshots below.
- **Training runner** (`homeassistant/packages/dd05_training.yaml`): a generic, timestamp-based segment runner (with differential writes and readback verification). HIIT is built from the settings-page parameters (recommended defaults: 14 rounds, `45:00` total). The old fixed *Interval 10 min* program is now a compatibility wrapper: Assist / Google scenes that still call `script.training_interval_10` turn HIIT on and start the current settings. The standalone Training dashboard (`dashboards/training.yaml`) is unchanged.
- **Voice**: Assist custom sentences in Traditional Chinese (開始走 / 暫停走 / 停止走 / 加速度 / 減速度 / 加坡度 / 減坡度, plus starting, pausing and ending interval training or HIIT), and the same scripts exposed to Google Assistant as scenes.

**Main view:** speed and incline, time and distance, program status, start/pause/stop, plus the HIIT toggle and a link to settings. With HIIT on, Start runs the program from the current settings; with HIIT off it is manual control.

![Treadmill main view](docs/images/remote.png)

**Settings:** +/- steppers for warm-up, fast walk, recovery, cool-down and rounds. +/- writes the helpers immediately; Save only returns to the main view.

![Treadmill settings](docs/images/settings.png)

## Tested setup

| Item | Version / value |
|---|---|
| Treadmill | BGYM DD05 (reports as **FitShow FS-BT-F5**, firmware `V1.0.5beta`, hardware `V1.0.0`) |
| BLE service | Fitness Machine Service (FTMS, UUID `0x1826`) |
| Range exposed in HA | speed 1.0–6.0 km/h (step 0.1), incline 0–15 % (step 1) |
| Home Assistant | 2026.10.4 (Docker) |
| Integration | [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6 (pyftms 0.4.10) + the patch in `patches/` |
| Bluetooth proxy | ESP32-C3 (esp32-c3-devkitm-1), ESPHome 2026.10.1, **ESP-IDF pinned to 5.5.5** |
| Custom card | [button-card](https://github.com/custom-cards/button-card) **7.0.1** (HACS; required for the treadmill dashboard) |

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
        ├── packages/dd05_treadmill_remote.yaml  → remote speed/incline scripts
        ├── packages/dd05_training.yaml          → helpers, HIIT runner, remote wrappers, safety watchdog
        ├── dashboards (Treadmill remote/settings, optional Training)
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
docs/                          architecture notes, upstream notes, dated debug logs, dashboard screenshots (`docs/images/`)
```

## Installation

This chapter is for **other BGYM DD05 owners who want to apply this project to their own Home Assistant (HA)**. Follow the steps in order. `/config` means your HA configuration folder (for Docker it is the folder mounted as `/config` in the container; on HA OS you can reach it with Samba, File editor or an SSH-type add-on).

### 0. Prerequisites

- **Home Assistant**: Docker or HA OS both work. The author's setup is Docker (see [Tested setup](#tested-setup), Home Assistant 2026.10.4). Bluetooth goes through an ESPHome proxy, so the HA host does not need its own Bluetooth adapter.
- **Treadmill**: must support Bluetooth FTMS (Fitness Machine Service, `0x1826`). The DD05 is verified; other models are untested.
- **ESPHome Bluetooth proxy**: e.g. an ESP32-C3, placed near the treadmill (same room). See the next step and `esphome/bt-proxy-esp32c3.yaml`.
- **hassio-ftms version**: the patched files in this repo target hassio-ftms **0.24.6** (pyftms 0.4.10). With another version, do not overwrite files blindly; compare first.
- **button-card**: the treadmill dashboard uses the `custom:button-card` card. Install [button-card](https://github.com/custom-cards/button-card) from HACS first (tested 7.0.1). The Training dashboard still uses built-in cards only.
- The DD05 accepts only one Bluetooth connection at a time, so close the FitShow phone app before using it.

### 1. Bluetooth proxy (ESP32-C3 + ESPHome)

1. Copy `esphome/secrets.yaml.example` to `esphome/secrets.yaml` and fill it in.
2. Flash `esphome/bt-proxy-esp32c3.yaml` (first time over USB, later OTA).
3. Place the proxy close to the treadmill (same room). Home Assistant will discover it through the ESPHome integration.

**Why ESP-IDF 5.5.5?** With ESPHome 2026.10.1 the default framework was ESP-IDF 5.5.6. On that build the proxy connected to the DD05 but GATT service discovery ended early, so the FTMS service `0x1826` was never reported and the integration could not set up. Raising `CONFIG_BT_GATTC_MAX_CACHE_CHAR` did not help. Pinning `framework: version: 5.5.5` fixed it. ESPHome prints a "not the recommended version" warning; this is expected. Re-test whenever you upgrade ESPHome; a newer IDF may fix it, in which case you can drop the pin.

The author's proxies ran without API encryption or an OTA password; this example adds both as recommended hardening.

### 2. hassio-ftms integration + patch

1. Install [hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6 (HACS custom repository or manual copy to `/config/custom_components/ftms/`).
2. Apply the Training Status patch (put the patch file from `patches/` somewhere reachable and run in `/config`; try `--dry-run` first, revert with `-R`, see `patches/README.md`):
   ```bash
   cd /config
   patch -p1 < patches/hassio-ftms-0.24.6-lenient-training-status.patch
   ```
3. Copy the three files in `homeassistant/custom_components/ftms/` (`__init__.py`, `sensor.py`, `updater_patch.py`) over the corresponding paths under `/config/custom_components/ftms/`. `updater_patch.py` is new and must sit next to `__init__.py`. What they do:

   | File | Purpose |
   |---|---|
   | `__init__.py` | Lenient Training Status parsing; control timeout `CONTROL_TIMEOUT = 8.0` (pyftms' default of 2 s is too short for the DD05); loads `updater_patch` |
   | `sensor.py` | ENUM sensors keep `None` when the value is missing instead of falling back to `0` and raising `ValueError` |
   | `updater_patch.py` | Fixes pyftms 0.4.10 dropping whole notifications (`KeyError: 'step_count'`) because the DD05 alternates two kinds of Treadmill Data packets; without it speed/incline readings lag |

   See `patches/README.md` and `homeassistant/custom_components/ftms/README.md`.
4. Restart Home Assistant. The DD05 should be discovered via Bluetooth (FTMS). Add it. All YAML here uses entity IDs `*.treadmill_*` (the default when the device is named "Treadmill"); if yours differ, see [7. Entity name mapping](#7-entity-name-mapping) below.

> [!WARNING]
> **Updating hassio-ftms through HACS overwrites these changes.** After an update, re-apply the patch, copy the three files again and restart HA. Back up `/config/custom_components/ftms/` before updating. Without re-applying, the DD05 may again hit the Training Status parse error and laggy speed/incline readings.

**Upstream status:** these fixes are local monkey-patches. `docs/upstream-notes.md` is still an **unsubmitted draft** (issue title and body, pre-submit checklist) and cites two related comments under python-pyftms PR #60; the document records no merged upstream fix, so for now you must re-apply the patch after every update.

**What the patch does:** the DD05 sends *Training Status* notifications with flag bits that are undefined in the FTMS spec (e.g. `0x46`). pyftms 0.4.10 raises on them and the integration setup aborts. The patch keeps only the two spec-defined flag bits and, if a status still cannot be parsed, logs a warning and skips it instead of crashing. See `patches/README.md`. The proper long-term fix belongs upstream (pyftms / hassio-ftms); see `docs/upstream-notes.md`.

### 3. Files to copy

| Source in this repo | Destination in your HA | Notes |
|---|---|---|
| `homeassistant/packages/*.yaml` (`dd05_treadmill_remote.yaml`, `dd05_training.yaml`) | `/config/packages/` | Enable packages in `configuration.yaml` first (next step) |
| `dashboards/*.yaml` (`treadmill_remote.yaml`, `training.yaml`) | Not copied: create a dashboard and paste into the Raw configuration editor. The treadmill page needs button-card and the URL path must be `treadmill-remote` | See step 5 |
| `homeassistant/www/training/interval10_v2.svg` | `/config/www/training/interval10_v2.svg` | Chart used by the optional Training dashboard's *Interval 10 min* page |
| `homeassistant/custom_sentences/zh-TW/*.yaml` (`treadmill.yaml`, `training.yaml`) | `/config/custom_sentences/zh-TW/` | Assist sentences (optional) |
| `homeassistant/configuration-snippets/intent_script.yaml` | Merge into `configuration.yaml` | For Assist voice (optional) |
| `homeassistant/configuration-snippets/google_assistant.yaml` | Merge into the existing `google_assistant:` block of `configuration.yaml` | For Google voice (optional) |
| `homeassistant/configuration-snippets/homeassistant_packages.yaml` | Merge into `configuration.yaml` | Enables packages, once only |

### 4. Home Assistant packages

1. Enable packages (once): add the content of `homeassistant/configuration-snippets/homeassistant_packages.yaml` to `configuration.yaml` (if you already have a `homeassistant:` block, merge `packages:` into it; do not write two `homeassistant:` keys):
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Copy `homeassistant/packages/*.yaml` to `/config/packages/`.
3. Notifications: `script.training_notify` in `dd05_training.yaml` contains `notify.mobile_app_YOUR_PHONE` (the only occurrence in the repo). Replace it with your phone's notify service, or delete the whole `choose:` notification block. The script always creates a persistent notification inside HA first, so messages are still visible without the phone notification. See step 6.
4. Check the configuration, then restart (step 8). Populate the HIIT / settings-page defaults before first use, also in step 8.

### 5. Dashboards

1. Install [button-card](https://github.com/custom-cards/button-card) from HACS (tested 7.0.1). It is required for the treadmill dashboard.
2. If you also want the standalone Training dashboard, copy `homeassistant/www/training/interval10_v2.svg` to `/config/www/training/interval10_v2.svg` (restart HA once if `/config/www/` did not previously exist so `/local/training/interval10_v2.svg` is served).
3. Settings → Dashboards → Add dashboard, title e.g. "Treadmill", icon `mdi:walk`. **Set the URL path to `treadmill-remote`** (the settings subview navigates to `/treadmill-remote/custom` and back to `/treadmill-remote/remote`; if you choose another path, edit those two strings in the YAML). Open the dashboard → ⋮ → Edit → Raw configuration editor, and paste `dashboards/treadmill_remote.yaml`.
4. (Optional) Add a "Training" dashboard the same way (icon `mdi:run`) and paste `dashboards/training.yaml`. That file still uses only built-in cards and is unchanged since 2026-11-17. Note that its *Interval 10 min* Start button still calls `script.training_interval_10`, which now runs HIIT with the current settings rather than the old fixed 10-minute program. Day-to-day use is meant to go through the treadmill page.

### 6. Voice commands and notification / Google placeholders (optional)

Skip the voice parts if you use neither Assist nor Google; you should still handle the notification placeholder.

- **Phone notification placeholder:** replace `notify.mobile_app_YOUR_PHONE` in `homeassistant/packages/dd05_training.yaml` with your own notify service (search for `notify.mobile_app_` in Developer tools → Actions), or remove that step. Only `dd05_training.yaml` uses it; `dd05_treadmill_remote.yaml` and the dashboards contain no notification settings.
- **Assist (zh-TW):** copy `homeassistant/custom_sentences/zh-TW/*.yaml` to `/config/custom_sentences/zh-TW/`, merge `configuration-snippets/intent_script.yaml` into `configuration.yaml`, restart. The Assist language must be Traditional Chinese (zh-TW).
- **Google Assistant (manual YAML setup):** merge `configuration-snippets/google_assistant.yaml` into your existing `google_assistant:` block, restart, then call `google_assistant.request_sync`. Scripts show up in Google Home as scenes. Two placeholders in that file must be replaced with your own:
  - `project_id: YOUR_GOOGLE_PROJECT_ID`: your Google Cloud / Actions project ID.
  - `service_account: !include SERVICE_ACCOUNT.json`: your service-account key file (kept in `/config`; **never publish it or commit it to git**).

  If you already have Google Assistant configured, merge only the `script.*` items under `entity_config:`; do not overwrite your existing `project_id` or `service_account`.

| Say | Action |
|---|---|
| 開始走 / 走步機開始 | start / resume |
| 暫停走 / 走步機暫停 | pause |
| 停止走 / 走步機停止 | stop |
| 加速度 / 減速度 | speed +/- 0.5 km/h (only while the belt is moving) |
| 加坡度 / 減坡度 | incline +/- 1 % |
| 開始間歇訓練 / 開始 HIIT / 訓練暫停 / 繼續訓練 / 結束訓練 | turn HIIT on and start the current settings / pause-resume / end |

### 7. Entity name mapping

The packages and dashboards in this repo use only the treadmill entities below (checked file by file; `configuration-snippets` contains no treadmill entities, only `script.*`):

| Entity ID | Purpose | Used in |
|---|---|---|
| `sensor.treadmill_speed` | Current speed (belt-moving check, safety watchdog, readback verification) | `dd05_treadmill_remote.yaml`, `dd05_training.yaml`, both dashboards |
| `sensor.treadmill_inclination` | Current incline | same |
| `number.treadmill_speed` | Write target speed | `dd05_treadmill_remote.yaml`, `dd05_training.yaml` |
| `number.treadmill_inclination` | Write target incline | same |
| `button.treadmill_start_resume` | Start / resume | same |
| `button.treadmill_pause` | Pause | same |
| `button.treadmill_stop` | Stop | same |
| `sensor.treadmill_time_elapsed` | Elapsed time | `dashboards/treadmill_remote.yaml` only |
| `sensor.treadmill_distance_total` | Total distance | `dashboards/treadmill_remote.yaml` only |

Entities such as `sensor.treadmill_status` or `switch.treadmill_connection` are **not used** by the packages or dashboards, so their names do not matter.

If your entity IDs differ (for example the device is not named "Treadmill"), you have two options:

1. **(Easiest) Rename the entity IDs in HA:** Settings → Devices & services → Entities, open each entity in the table above → gear icon → change the entity ID to the name in the table. HA updates dashboards and scripts that reference them.
2. **Global search and replace:** in `packages/*.yaml` and `dashboards/*.yaml`, replace each entity ID above with yours (replace the full string, so you do not change `sensor.` but miss `number.` or `button.`).

### 8. Reload and verify

**1. Check the configuration:** Developer tools → YAML → Check configuration. Fix any errors before restarting.

**2. Restart vs. reload:**

| Situation | Action |
|---|---|
| First time adding `packages`, `custom_components/ftms` or `google_assistant` config | Restart HA |
| First time creating `/config/www/` (so `/local/` is served) | Restart HA |
| Later edits to scripts, input_number, template, intent_script, conversation (custom sentences) | Use the matching "Reload" in Developer tools → YAML; no restart needed |
| Updating hassio-ftms or re-applying the patch | Restart HA |

**3. Populate custom-program defaults after the first deploy:** the `input_number.training_custom_*` helpers intentionally omit `initial:` so reloads and restarts keep your settings, but they start empty. In Developer tools → Actions, call `input_number.set_value` for each one with the recommended defaults (14 rounds, total `45:00`):

| Entity | Value |
|---|---|
| `input_number.training_custom_rounds` | 14 |
| `input_number.training_custom_warmup_dur` / `_warmup_speed` / `_warmup_incline` | 90 / 3.0 / 0 |
| `input_number.training_custom_fast_dur` / `_fast_speed` / `_fast_incline` | 120 / 4.5 / 5 |
| `input_number.training_custom_rest_dur` / `_rest_speed` / `_rest_incline` | 60 / 3.0 / 0 |
| `input_number.training_custom_cooldown_dur` / `_cooldown_speed` / `_cooldown_incline` | 90 / 3.0 / 0 |

```yaml
action: input_number.set_value
target:
  entity_id: input_number.training_custom_rounds
data:
  value: 14
```

**4. Verification checklist:**

- The treadmill entities in the table above are not `unavailable` (`sensor.treadmill_status` may stay unavailable on the DD05; this is a known issue and can be ignored).
- The treadmill main view shows speed/incline, time and distance, the HIIT toggle and the settings entry. On the settings page the estimated total (`sensor.training_custom_total_mmss`) reads `45:00` with the defaults.
- **Do not run a program yet.** Stand on the treadmill with the safety key clipped on, leave HIIT off, and use the treadmill dashboard at the lowest speed: after Start, confirm the belt moves, speed +/− and incline +/− respond, and Stop stops it. Only then turn HIIT on and run a program.

### 9. Safety reminders and recovery

- Test at **low speed** first, ideally with someone nearby who can press Stop on the treadmill or pull the safety key at any time. See [Safety](#safety) below.
- **HA control has latency; a timeout does not mean the command was not executed.** pyftms' default control timeout is only 2 s, so when the DD05 answers slowly HA reports an error first and the command may take effect later (`docs/2026-11-16-dd05-debug-log.md` records a case where the belt started about 5 s after HA reported the timeout). On an error, check the treadmill's actual state instead of pressing Start repeatedly; this repo already raises the control timeout to 8 s.
- **DD05 occasionally unresponsive after an HA restart** (Bluetooth shows connected, but control writes time out and no status comes back; cause not yet found):
  1. **Power-cycle** the DD05 (unplug and replug).
  2. In HA, reload the **ESPHome proxy** device (Settings → Devices & services → ESPHome → the proxy → Reload).
  3. Reload the **FTMS integration**.
  4. Confirm control with manual start/pause before using a program.

## Training runner

- **Helpers**: `input_select.training_state` (`idle/starting/running/paused/resuming/finishing`, `initial: idle`), timestamps, current phase, round, last target, plus `input_boolean.training_hiit` (the main-view toggle; no `initial:`, so a restart restores the last on/off state).
- **`script.training_run`**: generic runner that takes `program_name` and a list of `segments` (`{name, round, dur, s0, i0, s1?, i1?, ramp_dur?, step?}`), computes elapsed time from timestamps (no drift), uses differential writes with a 0.5 s speed-to-incline gap, and verifies treadmill readback after 1.5 s (up to 4 attempts) so DD05 firmware doesn't drop or overwrite segment transitions.
- **`script.training_custom`**: reads a snapshot of the 13 `input_number.training_custom_*` helpers (rounds 5–30, per-phase duration 30–120 s, speed 2.0–6.0 km/h, incline 0–15 %) and hands the resulting HIIT program to `script.training_run`. Estimated total is shown by `sensor.training_custom_total_mmss` (recommended defaults: 14 rounds / `45:00`). The settings-page +/- steppers write these helpers.
- **`script.training_interval_10`**: compatibility wrapper (entity ID kept for existing Assist / Google scenes). It no longer embeds a fixed 10-minute program; it turns HIIT on and then calls `script.training_custom`. If a session is already paused, that is treated as resume.
- **`script.treadmill_remote_start` / `_pause` / `_stop`**: the treadmill main view's Start / Pause / Stop buttons call only these three. Start while paused resumes the program; with HIIT on and idle it starts the current settings; with HIIT off and idle it starts the belt manually.
- **`script.training_pause` / `script.training_end`**: pause ↔ resume toggle (re-applies target speed/incline on resume), and abort + stop.
- **Watchdog and wrap-up automations**: while running, if speed < 0.1 km/h for 3 s (stop button, safety key pulled), the sensor is unavailable for 10 s, or `script.training_run` exits unexpectedly (`automation.training_run_died_guard`), the program is cleaned up/aborted and you get a notification. After a normal finish, if the phase stays at "已完成" and the state is idle for 2 minutes, the phase is reset to "待機" (the treadmill is not touched).
- To add a program: write a definition script that builds `segments` and calls `script.training_run`. Do not copy `training_interval_10` any more; that script is now the HIIT wrapper.

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

- **2026-11-22**: Treadmill dashboard rebuilt with button-card (main view + settings subview), HIIT toggle and remote wrapper scripts; `script.training_interval_10` became a compatibility wrapper — see [docs/2026-11-22-treadmill-remote-hiit.md](docs/2026-11-22-treadmill-remote-hiit.md) (Traditional Chinese, times in Asia/Taipei).
- **2026-11-16**: Tests and fixes (timeouts, training runner, display dropouts), plus the segment-boundary speed overwrite bug discovered in initial live testing — see [docs/2026-11-16-dd05-debug-log.md](docs/2026-11-16-dd05-debug-log.md) (Traditional Chinese, times in Asia/Taipei).
- **2026-11-17**: Root-cause evidence & fix for the segment-boundary bug (verified in live testing), *Interval 10 min* v2 + SVG chart, 13-slider *Custom* program, and voice switch from 35 min to *Interval 10 min* — see [docs/2026-11-17-dd05-training-update.md](docs/2026-11-17-dd05-training-update.md) (Traditional Chinese, times in Asia/Taipei).
- **2026-11-18**: Full 30-minute live test of `script.training_custom` (32 segments, 31 transitions): 0 missed segments, 0 retries, 0 speed overwrites, confirming the 2026-11-17 transition fix — see [docs/2026-11-18-custom-interval-test.md](docs/2026-11-18-custom-interval-test.md) (Traditional Chinese, times in Asia/Taipei).

## Disclaimer

This is an unofficial community project. It is **not affiliated with, endorsed by, or supported by BGYM, FitShow, or Home Assistant / Nabu Casa**. All trademarks belong to their owners. Use at your own risk; you are responsible for safe operation of your equipment. Remote control of exercise equipment can cause injury. Modifying integrations may break on updates.

## License

See [LICENSE](LICENSE) for this project's own files. The file in `patches/` modifies hassio-ftms, which is licensed under Apache-2.0 (`patches/LICENSE-hassio-ftms-Apache-2.0`).

## Credits

- [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) and pyftms by Sergey Dudanov.
- [custom-cards/button-card](https://github.com/custom-cards/button-card).
- ESPHome Bluetooth proxy.
