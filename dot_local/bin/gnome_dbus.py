# ruff: file-ignore[implicit-namespace-package]  # scripts import it from their own directory, not a package
"""GNOME session D-Bus access shared by the display services in this directory."""

import dataclasses
from typing import Final

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # ruff: ignore[module-import-not-at-top-of-file] # require_version must run first


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DBusTarget:
    name: str
    path: str
    interface: str


MUTTER: Final = DBusTarget(
    name="org.gnome.Mutter.DisplayConfig",
    path="/org/gnome/Mutter/DisplayConfig",
    interface="org.gnome.Mutter.DisplayConfig",
)


def call(bus: Gio.DBusConnection, target: DBusTarget, method: str, args: GLib.Variant | None) -> GLib.Variant:
    return bus.call_sync(
        target.name, target.path, target.interface, method, args, None, Gio.DBusCallFlags.NONE, -1, None
    )


# Re-exported so importers get the GI versions pinned above instead of pinning them again
__all__ = ["MUTTER", "DBusTarget", "GLib", "Gio", "call"]
