# Upstream notes (draft - not yet submitted)

Target: https://github.com/dudanov/pyftms (parser) and/or https://github.com/dudanov/hassio-ftms

## Draft issue title
Training Status parse error aborts setup on FitShow FS-BT-F5 (BGYM DD05)

## Draft body
**Device:** BGYM DD05 walking pad, BLE name/model FitShow FS-BT-F5, firmware V1.0.5beta, hardware V1.0.0
**Versions:** hassio-ftms 0.24.6, pyftms 0.4.10, Home Assistant 2026.10.4, ESPHome Bluetooth proxy (ESP32-C3)

The treadmill sends Training Status (0x2AD3) notifications whose flags byte has
reserved bits set (e.g. `0x46`), and sometimes a status code outside the spec
(e.g. `83`, followed by a text payload). pyftms raises during parsing and the
config entry fails to set up.

Workaround used locally: mask the flags to the two defined bits (`& 0x03`) and
catch/log parse errors instead of propagating (patch attached).

Suggested fix: in the Training Status deserializer, ignore reserved flag bits and
map unknown status codes to an "Other/Unknown" value instead of raising, so one
non-conforming notification cannot break the whole integration.

## Before submitting
- Confirm the issue still exists on the latest hassio-ftms / pyftms release.
- Attach a debug log (`logger: logs: pyftms: debug`) with raw notification hex.
- Remove any personal data from logs (MAC addresses, IPs, hostnames).
