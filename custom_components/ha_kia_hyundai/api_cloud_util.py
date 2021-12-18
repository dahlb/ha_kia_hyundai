from .api_cloud_us_kia import ApiCloudUsKia
from .api_cloud_ca_kia import ApiCloudCaKia
from .api_cloud_ca_hyundai import ApiCloudCaHyundai
from .api_cloud_us_hyundai import ApiCloudUsHyundai
from .const import REGION_USA, REGION_CANADA, BRAND_KIA, BRAND_HYUNDAI


def api_cloud_for_region_and_brand(region: str, brand: str):
    if region == REGION_USA and brand == BRAND_KIA:
        return ApiCloudUsKia
    if region == REGION_USA and brand == BRAND_HYUNDAI:
        return ApiCloudUsHyundai
    if region == REGION_CANADA and brand == BRAND_KIA:
        return ApiCloudCaKia
    if region == REGION_CANADA and brand == BRAND_HYUNDAI:
        return ApiCloudCaHyundai
    return None
