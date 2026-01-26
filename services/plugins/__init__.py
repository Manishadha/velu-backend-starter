# services/plugins/__init__.py
from .catalog import PLUGINS, PluginDef, get_plugin  # type: ignore

__all__ = ["PLUGINS", "PluginDef", "get_plugin"]
