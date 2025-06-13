# custom_components/evlinkha/sensor.py

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, ICONS, USER_FIELDS, VEHICLE_FIELDS

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up EVLinkHA sensors."""
    user_coordinator = hass.data[DOMAIN].get(entry.entry_id)
    vehicle_coordinator = hass.data[DOMAIN].get(f"{entry.entry_id}_vehicle")

    entities = []

    # Skapa sensorer för userinfo
    for field, (label, unit) in USER_FIELDS.items():
        entities.append(EVLinkHASensor(user_coordinator, entry, field, label, unit))

    # Skapa sensorer för vehicle status, om coordinator finns
    if vehicle_coordinator:
        for field, (label, unit) in VEHICLE_FIELDS.items():
            entities.append(
                EVLinkHAVehicleSensor(vehicle_coordinator, entry, field, label, unit)
            )
    
    entities.append(
        EVLinkHALocation(
            vehicle_coordinator,  # basera på status‐coordinatorn
            entry
        )
    )

    async_add_entities(entities)


class EVLinkHASensor(CoordinatorEntity, SensorEntity):
    """Sensor för användarinformation."""

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
        # Fallback till entry_id om data saknas
        return f"{DOMAIN}-{self._entry.entry_id}-{self._field}"


class EVLinkHAVehicleSensor(CoordinatorEntity, SensorEntity):
    """Sensor för fordonsstatus."""

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
        # Hämta värdet ur din nested JSON
        data = self.coordinator.data or {}
        parts = self._field.split(".")
        val = data
        for p in parts:
            if not isinstance(val, dict):
                val = None
                break
            val = val.get(p)

        # Speciell hantering för null-värden på chargeRate och chargeTimeRemaining
        if self._field in ("chargeState.chargeRate", "chargeState.chargeTimeRemaining"):
            return "--" if val is None else val

        # Övriga sensorer: returnera som vanligt (None → Unknown)
        return val

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        return ICONS.get(self._field)

    @property
    def unique_id(self):
        # Enhetligt id utan beroende av svarsdatan
        return f"{DOMAIN}-{self._entry.entry_id}-vehicle-{self._field}"

class EVLinkHALocation(CoordinatorEntity, SensorEntity):
    """Template‐sensor för fordonsposition med lat/lon‐attribut."""

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
        """Använd vehicleName som state (eller valfritt fält)."""
        data = self.coordinator.data or {}
        # vehicleName kommer från /status/:vehicle_id
        return data.get("vehicleName") or "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Exponera latitude/longitude som attribut."""
        data = self.coordinator.data or {}
        loc = data.get("location", {})
        return {
            "latitude":  loc.get("latitude"),
            "longitude": loc.get("longitude"),
        }

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}-{self._entry.entry_id}-location"
