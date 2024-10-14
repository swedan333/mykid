import logging
from datetime import datetime, timedelta
from typing import List

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt

from .const import DOMAIN, CONF_PHONE, CONF_PASSWORD, CONF_CALENDAR
from .mykid_api import MyKidAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the MyKid calendar platform."""
    coordinator = MyKidCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([MyKidCalendar(coordinator, entry)], True)

class MyKidCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to manage fetching data from MyKid."""

    def __init__(self, hass, entry):
        """Initialize the coordinator."""
        self.api = MyKidAPI(entry.data[CONF_PHONE], entry.data[CONF_PASSWORD])
        self.calendar_entity_id = entry.data[CONF_CALENDAR]
        super().__init__(
            hass,
            _LOGGER,
            name="MyKid Calendar",
            update_interval=timedelta(minutes=60),
        )

    async def _async_update_data(self):
        """Fetch data from MyKid."""
        now = datetime.now()
        start_date = now.strftime('%Y-%m-%d')
        end_date = (now + timedelta(days=30)).strftime('%Y-%m-%d')

        events = await self.hass.async_add_executor_job(
            self.api.fetch_events, start_date, end_date
        )
        return events

class MyKidCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of a MyKid Calendar."""

    def __init__(self, coordinator, entry):
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        self._name = "MyKid Calendar"
        self.calendar_entity_id = entry.data[CONF_CALENDAR]
        self._event = None

    @property
    def name(self):
        """Return the name of the calendar."""
        return self._name

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(self, hass, start_date, end_date) -> List[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = []

        for event in self.coordinator.data:
            event_start = dt.parse_datetime(f"{event['date_from']} {event['time_from']}")
            event_end = dt.parse_datetime(f"{event['date_from']} {event['time_to']}")
            if event_end < start_date or event_start > end_date:
                continue

            cal_event = CalendarEvent(
                summary=event['title'],
                start=event_start,
                end=event_end,
                description=event['description'],
                location="MyKid"
            )
            events.append(cal_event)

        return events

    async def async_update(self):
        """Update the state of the calendar."""
        await self.coordinator.async_request_refresh()
        now = dt.now()
        future_events = [
            event for event in self.coordinator.data
            if dt.parse_datetime(f"{event['date_from']} {event['time_from']}") >= now
        ]
        future_events.sort(
            key=lambda x: dt.parse_datetime(f"{x['date_from']} {x['time_from']}")
        )
        if future_events:
            next_event = future_events[0]
            event_start = dt.parse_datetime(f"{next_event['date_from']} {next_event['time_from']}")
            event_end = dt.parse_datetime(f"{next_event['date_from']} {next_event['time_to']}")
            self._event = CalendarEvent(
                summary=next_event['title'],
                start=event_start,
                end=event_end,
                description=next_event['description'],
                location="MyKid"
            )
        else:
            self._event = None
