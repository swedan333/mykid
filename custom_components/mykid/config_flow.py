import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_PHONE, CONF_PASSWORD, CONF_CALENDAR
from .mykid_api import MyKidAPI

_LOGGER = logging.getLogger(__name__)

class MyKidConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyKid."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            phone = user_input[CONF_PHONE]
            password = user_input[CONF_PASSWORD]

            # Validate the credentials
            api = MyKidAPI(phone, password)
            valid = await self.hass.async_add_executor_job(api.validate_credentials)

            if valid:
                # Move to the next step to select calendar
                self.phone = phone
                self.password = password
                return await self.async_step_calendar()
            else:
                errors["base"] = "auth"

        data_schema = vol.Schema({
            vol.Required(CONF_PHONE): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_calendar(self, user_input=None):
        """Handle the calendar selection step."""
        errors = {}
        if user_input is not None:
            calendar_entity = user_input[CONF_CALENDAR]
            return self.async_create_entry(
                title="MyKid Calendar",
                data={
                    CONF_PHONE: self.phone,
                    CONF_PASSWORD: self.password,
                    CONF_CALENDAR: calendar_entity,
                },
            )

        calendars = [
            entity_id
            for entity_id in self.hass.states.async_entity_ids("calendar")
        ]

        if not calendars:
            errors["base"] = "no_calendars"
            return self.async_show_form(
                step_id="calendar", errors=errors
            )

        data_schema = vol.Schema({
            vol.Required(CONF_CALENDAR): vol.In(calendars),
        })

        return self.async_show_form(
            step_id="calendar", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MyKidOptionsFlowHandler(config_entry)

class MyKidOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_CALENDAR, default=self.config_entry.data.get(CONF_CALENDAR)): vol.In(
                [entity_id for entity_id in self.hass.states.async_entity_ids("calendar")]
            ),
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
