# custom_components/evlinkha/sensor.py

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, ICONS, USER_FIELDS, VEHICLE_FIELDS, WEBHOOK_FIELDS
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EVLinkHA sensors."""
    user_coordinator = hass.data[DOMAIN].get(entry.entry_id)
    vehicle_coordinator = hass.data[DOMAIN].get(f"{entry.entry_id}_vehicle")

    entities = []

    # Hämta capabilities från senaste vehicle-status
    vehicle_data = vehicle_coordinator.data or {}
    capabilities = vehicle_data.get("capabilities", {})
    _LOGGER.debug("[EVLinkHA] Vehicle capabilities: %s", capabilities)

    def is_field_capable(field):
        cap_key = field.split(".")[0]
        cap = capabilities.get(cap_key, {})
        is_cap = cap.get("isCapable", True)  # Default True för bakåtkompabilitet
        _LOGGER.debug("[EVLinkHA] Field '%s' capability '%s': %s", field, cap_key, is_cap)
        return is_cap

    # Userinfo sensors
    for field, (label, unit) in USER_FIELDS.items():
        entities.append(EVLinkHASensor(user_coordinator, entry, field, label, unit))

    # Vehicle status sensors, nu med filtrering!
    if vehicle_coordinator:
        for field, (label, unit) in VEHICLE_FIELDS.items():
            if is_field_capable(field):
                entities.append(
                    EVLinkHAVehicleSensor(vehicle_coordinator, entry, field, label, unit)
                )
                _LOGGER.warning(
                    "[EVLinkHA] Sensor created: %s, field: %s",
                    f"{DOMAIN}-{entry.entry_id}-vehicle-{field}",
                    field,
                )
            else:
                _LOGGER.warning(
                    "[EVLinkHA] Skipping sensor for field '%s' since capability '%s' isCapable: False",
                    field, field.split(".")[0]
                )

    entities.append(
        EVLinkHALocation(
            vehicle_coordinator,  # based on the status coordinator
            entry
        )
    )

    for field, (label, unit) in WEBHOOK_FIELDS.items():
        entities.append(EVLinkHAWebhookIdSensor(user_coordinator, entry, field, label, unit))

    async_add_entities(entities)


class EVLinkHASensor(CoordinatorEntity, SensorEntity):
    """Sensor for user information."""

    def __init__(self, coordinator, entry, field, name, unit):
        super().__init__(coordinator)
        self._entry = entry
        self._field = field
        self._name = name
        self._unit = unit

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "EVLinkHA",
            "manufacturer": "Roger Aspelin",
            "model": "EVLinkHA Integration",
        }

    @property
    def name(self):
        return f"EVLinkHA {self._name}"

    @property
    def state(self):
        data = self.coordinator.data or {}
        return data.get(self._field)

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        return ICONS.get(self._field)

    @property
    def unique_id(self):
        # Fallback to entry_id if data is missing
        return f"{DOMAIN}-{self._entry.entry_id}-{self._field}"

class EVLinkHAVehicleSensor(CoordinatorEntity, SensorEntity):
    """Sensor for vehicle status."""

    def __init__(self, coordinator, entry, field, name, unit):
        super().__init__(coordinator)
        self._entry = entry
        self._field = field
        self._name = name
        self._unit = unit

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "EVLinkHA",
            "manufacturer": "Roger Aspelin",
            "model": "EVLinkHA Integration",
        }

    @property
    def name(self):
        return f"EVLinkHA {self._name}"

    @property
    def state(self):
        # Retrieve the value from the nested JSON
        data = self.coordinator.data or {}
        parts = self._field.split(".")
        val = data
        for p in parts:
            if not isinstance(val, dict):
                val = None
                break
            val = val.get(p)

        # Special handling for null values on chargeRate and chargeTimeRemaining
        if self._field in ("chargeState.chargeRate", "chargeState.chargeTimeRemaining"):
            return "--" if val is None else val

        # Other sensors: return as usual (None → Unknown)
        return val

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        return ICONS.get(self._field)

    @property
    def unique_id(self):
        # Consistent id independent of response data
        return f"{DOMAIN}-{self._entry.entry_id}-vehicle-{self._field}"

class EVLinkHALocation(CoordinatorEntity, SensorEntity):
    """Template sensor for vehicle position with lat/lon attributes."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "EVLinkHA",
            "manufacturer": "Roger Aspelin",
            "model": "EVLinkHA Integration",
        }

    @property
    def name(self) -> str:
        return "EVLinkHA Location"

    @property
    def state(self) -> str:
        """Use vehicleName as the state (or any field)."""
        data = self.coordinator.data or {}
        # vehicleName comes from /status/:vehicle_id
        return data.get("vehicleName") or "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Expose latitude/longitude as attributes."""
        data = self.coordinator.data or {}
        loc = data.get("location", {})
        return {
            "latitude":  loc.get("latitude"),
            "longitude": loc.get("longitude"),
        }

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}-{self._entry.entry_id}-location"

class EVLinkHAWebhookIdSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, field, name, unit):
        super().__init__(coordinator)
        self._entry = entry
        self._field = field
        self._name = name
        self._unit = unit

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "EVLinkHA",
            "manufacturer": "Roger Aspelin",
            "model": "EVLinkHA Integration",
        }

    @property
    def name(self):
        return f"EVLinkHA {self._name}"

    @property
    def state(self):
        # Returnera entry_id som är unikt för denna integration/instans.
        return self._entry.entry_id

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        return ICONS.get(self._field)

    @property
    def unique_id(self):
        # Fallback to entry_id if data is missing
        return f"{DOMAIN}-{self._entry.entry_id}-{self._field}"
