"""Local patch for pyftms 0.4.10 ``DataUpdater._on_notify`` (2026-11-16).

Problem: the original computes ``self._result.items() ^ self._prev.items()``
and then reads ``self._result[k]`` for every key of that symmetric difference.
A key that exists only in ``_prev`` (e.g. ``step_count`` was in the previous
packet but not in this one -- BGYM DD05 / FitShow alternates packets with
different flags) raises ``KeyError``.  The exception leaves ``_result``
uncleared and ``_prev`` stale, and the whole notification is dropped.

Fix: only look at the keys present in the current (merged) packet, compare them
with the last known value, merge the changes into ``_prev`` (so fields missing
from alternating packets are remembered), and always clear ``_result`` on a
complete packet, even on error.

Kept from the original: null-packet filter, "More Data" merge behaviour,
``UpdateEvent(event_id="update", event_data=dict)`` delivered via ``self._cb``.

This module has no homeassistant dependency; it is imported by ``__init__.py``
and applied at import time (idempotent).
Revert: remove the import from ``__init__.py``.
"""

import logging
from typing import cast

from pyftms.client.backends.event import UpdateEvent, UpdateEventData
from pyftms.client.backends.updater import DataUpdater

_LOGGER = logging.getLogger(__name__)

_MISSING = object()

# Keep the pristine function even if this module is reloaded.
_orig_on_notify = getattr(DataUpdater, "_ftms_orig_on_notify", DataUpdater._on_notify)


def _fixed_on_notify(self, c, data):
    keep_result = False  # True only while waiting for 'More Data' packets

    try:
        _LOGGER.debug("Received notify: %s", bytes(data).hex(" ").upper())
        data_ = self._serializer.deserialize(data)._asdict()
        _LOGGER.debug("Received notify dict: %s", data_)
        self._result |= data_

        # If `More Data` bit is set - we must wait for other messages.
        if data[0] & 1:
            keep_result = True
            _LOGGER.debug("'More Data' bit is set. Waiting for next data.")
            return

        # Some devices send a lot of null packets during wakeup and sleep mode.
        if any(self._result.values()):
            # Only fields present in this packet can change; compare by value
            # (does not require hashable values, never touches absent keys).
            update = {
                k: v
                for k, v in self._result.items()
                if self._prev.get(k, _MISSING) != v
            }

            if update:
                _LOGGER.debug("Update data: %s", update)
                event = UpdateEvent(
                    event_id="update", event_data=cast(UpdateEventData, update)
                )
                self._cb(event)
                # Merge: remember last value of every field, including those
                # absent from the next (alternating-flags) packets.
                self._prev |= self._result
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning(
            "Dropped FTMS notify %s: %r", bytes(data).hex(" ").upper(), exc
        )
    finally:
        # Complete packet, null packet or ANY exception: never leave residue.
        if not keep_result:
            self._result.clear()


def apply() -> None:
    """Apply the patch (idempotent)."""
    if getattr(DataUpdater, "_ftms_patched", False):
        return

    DataUpdater._ftms_orig_on_notify = _orig_on_notify
    DataUpdater._on_notify = _fixed_on_notify
    DataUpdater._ftms_patched = True
    _LOGGER.info("Applied FTMS DataUpdater._on_notify patch (KeyError fix).")


apply()
