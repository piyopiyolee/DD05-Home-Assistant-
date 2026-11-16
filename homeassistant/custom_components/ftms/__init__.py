"""The FTMS integration."""

import logging

import pyftms
from bleak.exc import BleakError
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_SENSORS,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import DataCoordinator
from .models import FtmsData

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)

CONTROL_TIMEOUT = 8.0

# Local patch (2026-11-14): BGYM DD05 / FitShow FS-BT-F5 sends Training Status
# flags with undefined bits (e.g. 0x46); pyftms rejects them and aborts setup.
# Keep only the two spec-defined flag bits; on any parse error log and skip.
# Revert: restore backups-ftms-20261114-2243\ftms__init__.py.orig
from pyftms.client.backends.controller import MachineController as _FtmsMC

_orig_on_training_status = _FtmsMC._on_training_status


def _lenient_on_training_status(self, c, data):
    try:
        _LOGGER.debug("FTMS raw training status bytes: %s", bytes(data).hex())
        data = bytearray(data)
        if data:
            data[0] &= 0x03
        _orig_on_training_status(self, c, data)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Skipping unparsable FTMS training status %s: %s", bytes(data).hex(), exc)


_FtmsMC._on_training_status = _lenient_on_training_status

# Local patch (2026-11-16): pyftms DataUpdater._on_notify raises
# KeyError('step_count') when a Treadmill Data packet omits a field present in
# the previous packet, dropping the whole notification. See updater_patch.py
# (must be deployed next to this file). Applied at import time.
from . import updater_patch as _updater_patch  # noqa: E402,F401

type FtmsConfigEntry = ConfigEntry[FtmsData]


async def async_unload_entry(hass: HomeAssistant, entry: FtmsConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.ftms.disconnect()
        bluetooth.async_rediscover_address(hass, entry.runtime_data.ftms.address)

    return unload_ok


async def async_setup_entry(hass: HomeAssistant, entry: FtmsConfigEntry) -> bool:
    """Set up device from a config entry."""

    address: str = entry.data[CONF_ADDRESS]

    if not (srv_info := bluetooth.async_last_service_info(hass, address)):
        raise ConfigEntryNotReady(translation_key="device_not_found")

    def _on_disconnect(ftms_: pyftms.FitnessMachine) -> None:
        """Disconnect handler. Reload entry on disconnect."""

        if ftms_.need_connect:
            hass.config_entries.async_schedule_reload(entry.entry_id)

    try:
        ftms = pyftms.get_client(
            srv_info.device,
            srv_info.advertisement,
            timeout=CONTROL_TIMEOUT,
            on_disconnect=_on_disconnect,
        )

    except pyftms.NotFitnessMachineError:
        raise ConfigEntryNotReady(translation_key="ftms_error")

    coordinator = DataCoordinator(hass, ftms)

    try:
        await ftms.connect()

    except BleakError as exc:
        raise ConfigEntryNotReady(translation_key="connection_failed") from exc

    assert ftms.machine_type.name

    _LOGGER.debug(f"Device Information: {ftms.device_info}")
    _LOGGER.debug(f"Machine type: {ftms.machine_type.name}")
    _LOGGER.debug(f"Available sensors: {ftms.available_properties}")
    _LOGGER.debug(f"Supported settings: {ftms.supported_settings}")
    _LOGGER.debug(f"Supported ranges: {ftms.supported_ranges}")

    unique_id = "".join(
        x for x in ftms.device_info.get("serial_number", address) if x.isalnum()
    ).lower()

    _LOGGER.debug(f"Registered new FTMS device. UniqueID is '{unique_id}'.")

    device_info = dr.DeviceInfo(
        connections={(dr.CONNECTION_BLUETOOTH, ftms.address)},
        identifiers={(DOMAIN, unique_id)},
        translation_key=ftms.machine_type.name.lower(),
        **ftms.device_info,
    )

    entry.runtime_data = FtmsData(
        entry_id=entry.entry_id,
        unique_id=unique_id,
        device_info=device_info,
        ftms=ftms,
        coordinator=coordinator,
        sensors=entry.options[CONF_SENSORS],
    )

    @callback
    def _async_on_ble_event(
        srv_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Update from a ble callback."""

        ftms.set_ble_device_and_advertisement_data(
            srv_info.device, srv_info.advertisement
        )

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_on_ble_event,
            BluetoothCallbackMatcher(address=address),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    # Platforms initialization
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_entry_update_handler))

    async def _async_hass_stop_handler(event: Event) -> None:
        """Close the connection."""

        await ftms.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_hass_stop_handler)
    )

    return True


async def _async_entry_update_handler(
    hass: HomeAssistant, entry: FtmsConfigEntry
) -> None:
    """Options update handler."""

    if entry.options[CONF_SENSORS] != entry.runtime_data.sensors:
        hass.config_entries.async_schedule_reload(entry.entry_id)
