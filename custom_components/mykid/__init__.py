import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the MyKid integration."""
    # We don't support YAML configuration, so return True
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up MyKid from a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "calendar")
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "calendar")
    return True
