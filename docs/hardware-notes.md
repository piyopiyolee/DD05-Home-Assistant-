# Hardware & BLE notes

- **Treadmill:** BGYM DD05. BLE module identifies as FitShow **FS-BT-F5**
  (firmware `V1.0.5beta`, hardware `V1.0.0`). Advertises FTMS service data `0x1826`.
- **One connection only:** while the FitShow (or other) phone app is connected,
  Home Assistant cannot connect. Close the app / disable phone Bluetooth.
- **Start delay:** after "start", the belt counts down a few seconds before moving.
- **Proxy placement:** a proxy in the same room as the treadmill gave a stable
  connection; through a wall it was noticeably worse. The author runs four
  ESP32-C3 proxies and pins the treadmill room's proxy area in HA.
- **ESP-IDF:** ESPHome 2026.10.1 with default ESP-IDF 5.5.6 → GATT discovery cut
  short, FTMS service never reported. `CONFIG_BT_GATTC_MAX_CACHE_CHAR: "100"` on
  5.5.6 did not fix it. Pinning ESP-IDF **5.5.5** fixed it (all proxies flashed
  with the same build).
- **Entities created by hassio-ftms (as named on the author's system):**
  `sensor.treadmill_speed`, `sensor.treadmill_inclination`, `sensor.treadmill_ramp_angle`,
  `sensor.treadmill_distance_total`, `sensor.treadmill_energy_total`,
  `sensor.treadmill_time_elapsed`, `sensor.treadmill_heart_rate`, `sensor.treadmill_status`,
  `number.treadmill_speed`, `number.treadmill_inclination`,
  `button.treadmill_start_resume`, `button.treadmill_pause`, `button.treadmill_stop`,
  `button.treadmill_reset`, `switch.treadmill_connection`.
