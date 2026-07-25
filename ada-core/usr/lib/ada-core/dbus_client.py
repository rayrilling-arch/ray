"""D-Bus client for org.popos.AdaCore.Think."""

from __future__ import annotations

import dbus

BUS_NAME = "org.popos.AdaCore"
OBJECT_PATH = "/org/popos/AdaCore"
INTERFACE = "org.popos.AdaCore"
DEFAULT_TIMEOUT_MS = 120_000


class AdaCoreUnavailable(Exception):
    """Raised when the Ada Core D-Bus service is not reachable."""


def think(message: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> str:
    try:
        bus = dbus.SystemBus()
        proxy = bus.get_object(BUS_NAME, OBJECT_PATH, follow_name_owner_changes=True)
        iface = dbus.Interface(proxy, INTERFACE)
        result = iface.Think(message, timeout=timeout_ms)
        return str(result)
    except dbus.exceptions.DBusException as exc:
        raise AdaCoreUnavailable(str(exc)) from exc
