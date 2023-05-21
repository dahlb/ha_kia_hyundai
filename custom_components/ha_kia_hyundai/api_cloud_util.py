import logging
from .api_cloud_us_kia import ApiCloudUsKia
from .const import REGION_USA, BRAND_KIA

_LOGGER = logging.getLogger(__name__)


def api_cloud_for_region_and_brand(region: str, brand: str):
    if region == REGION_USA and brand == BRAND_KIA:
        _LOGGER.debug("US KIA in use")
        return ApiCloudUsKia
    return None
