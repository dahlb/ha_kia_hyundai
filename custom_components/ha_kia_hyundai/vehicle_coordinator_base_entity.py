import logging
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from . import VehicleCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VehicleCoordinatorBaseEntity(CoordinatorEntity[VehicleCoordinator]):
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.vehicle_id)},
            "name": self.coordinator.vehicle_name,
            "manufacturer": "US Kia",
            "model": self.coordinator.vehicle_model,
            "via_device": (DOMAIN, self.coordinator.vehicle_id),
        }
