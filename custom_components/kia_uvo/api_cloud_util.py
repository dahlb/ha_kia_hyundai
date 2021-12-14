from .api_cloud_us_kia import ApiCloudUsKia
from .const import (
    REGION_USA,
    REGION_CANADA,
    BRAND_KIA,
    BRAND_HYUNDAI
)


def api_cloud_for_region_and_brand(region: str, brand: str):
    if region == REGION_USA and brand == BRAND_KIA:
        return ApiCloudUsKia
    return None
