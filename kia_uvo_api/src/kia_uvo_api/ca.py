import logging

import time
from abc import ABC, abstractmethod
from aiohttp import ClientSession, ClientResponse, ClientError

from .auth_error import AuthError
from .const import CA_TEMP_RANGE

_LOGGER = logging.getLogger(__name__)


def convert_set_temp_to_api_from_celsius_value(set_temp):
    set_temp = CA_TEMP_RANGE.index(set_temp)
    set_temp = hex(set_temp).split("x")
    set_temp = set_temp[1] + "H"
    return set_temp.zfill(3).upper()


def request_with_logging_and_errors_raised(func):
    async def request_with_logging_wrapper(*args, **kwargs):
        url = kwargs["url"]
        json_body = kwargs.get("json_body")
        if json_body is not None:
            _LOGGER.debug(f"sending {url} request with {json_body}")
        else:
            _LOGGER.debug(f"sending {url} request")
        response = await func(*args, **kwargs)
        _LOGGER.debug(f"response headers:{response.headers}")
        response_text = await response.text()
        _LOGGER.debug(f"response text:{response_text}")
        response_json = await response.json()
        if response_json["responseHeader"]["responseCode"] == 0:
            return response
        # still need to add error code for expired token
        if response_json["error"]["errorCode"] == 7404:
            _LOGGER.debug(f"invalid password")
            raise AuthError(response_json["error"]["errorDesc"])
        response_text = await response.text()
        _LOGGER.error(f"error: unknown error response {response_text}")
        raise ClientError

    return request_with_logging_wrapper


class Ca(ABC):
    def __init__(self, client_session: ClientSession = None):
        if client_session is None:
            self.api_session = ClientSession(raise_for_status=True)
        else:
            self.api_session = client_session

    async def cleanup_client_session(self):
        await self.api_session.close()

    @property
    @abstractmethod
    def base_url(self):
        pass

    @property
    def api_url(self):
        return "https://" + self.base_url + "/tods/api/"

    def _api_headers(
        self,
        access_token: str = None,
        vehicle_id: str = None,
        pin_token: str = None,
        xid: str = None,
    ) -> dict:
        headers = {
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
            "host": self.base_url,
            "origin": "https://" + self.base_url,
            "referer": "https://" + self.base_url + "/login",
            "from": "SPA",
            "language": "0",
            "offset": str(int(time.localtime().tm_gmtoff / 60 / 60)),
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        if access_token is not None:
            headers["accessToken"] = access_token
        if vehicle_id is not None:
            headers["vehicleId"] = vehicle_id
        if pin_token is not None:
            headers["pAuth"] = pin_token
        if xid is not None:
            headers["transactionId"] = xid

        return headers

    @request_with_logging_and_errors_raised
    async def _post_request_with_logging_and_errors_raised(
        self,
        access_token: str,
        vehicle_id: str,
        url: str,
        json_body: dict = None,
        pin_token: str = None,
        xid: str = None,
    ) -> ClientResponse:
        pin = json_body.get("pin")
        if pin is not None and pin_token is None and not url.endswith("vrfypin"):
            pin_token_response = await self.get_pin_token(access_token, pin)
            pin_token = pin_token_response["pAuth"]

        headers = self._api_headers(access_token, vehicle_id, pin_token, xid)
        return await self.api_session.post(url=url, json=json_body, headers=headers)

    async def login(self, username: str, password: str) -> {str: str}:
        url = self.api_url + "lgn"
        json_body = {"loginId": username, "password": password}
        response: ClientResponse = (
            await self._post_request_with_logging_and_errors_raised(
                access_token=None, vehicle_id=None, url=url, json_body=json_body
            )
        )
        response_json = await response.json()
        access_token = response_json["result"]["accessToken"]
        refresh_token = response_json["result"]["refreshToken"]
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def get_vehicles(self, access_token: str):
        url = self.api_url + "vhcllst"
        response: ClientResponse = (
            await self._post_request_with_logging_and_errors_raised(
                access_token=access_token, vehicle_id=None, url=url
            )
        )
        response_json = await response.json()
        return response_json["result"]

    async def get_cached_vehicle_status(self, access_token: str, vehicle_id: str):
        url = self.api_url + "lstvhclsts"
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token, vehicle_id=vehicle_id, url=url
        )
        response_json = await response.json()
        return response_json["result"]

    async def get_next_service_status(self, access_token: str, vehicle_id: str):
        url = self.api_url + "nxtsvc"
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token, vehicle_id=vehicle_id, url=url
        )
        response_json = await response.json()
        return response_json["result"]

    async def get_pin_token(self, access_token: str, pin: str) -> dict[str, any]:
        url = self.api_url + "vrfypin"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token, url=url, json_body=json_body
        )
        response_json = await response.json()
        return response_json["result"]

    async def get_location(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ):
        url = self.api_url + "fndmcr"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            pin_token=pin_token,
            vehicle_id=vehicle_id,
            url=url,
            json_body=json_body,
        )
        response_json = await response.json()
        return response_json["result"]

    async def request_vehicle_data_sync(self, access_token: str, vehicle_id: str):
        url = self.api_url + "rltmvhclsts"
        await self._post_request_with_logging_and_errors_raised(
            access_token=access_token, vehicle_id=vehicle_id, url=url
        )

    async def check_last_action_status(
        self,
        access_token: str,
        vehicle_id: str,
        pin: str,
        xid: str,
        pin_token: str = None,
    ) -> dict:
        url = self.api_url + "rmtsts"

        if pin_token is None:
            pin_token_response = await self.get_pin_token(access_token, pin)
            pin_token = pin_token_response["pAuth"]

        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            xid=xid,
        )
        response_json = await response.json()
        return response_json["result"]

    async def lock(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ) -> str:
        url = self.api_url + "drlck"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def unlock(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ) -> str:
        url = self.api_url + "drulck"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def start_climate(
        self,
        access_token: str,
        vehicle_id: str,
        pin: str,
        set_temp,
        duration,
        defrost,
        climate,
        heating,
        pin_token: str = None,
    ):
        url = self.api_url + "rmtstrt"

        json_body = {
            "setting": {
                "airCtrl": int(climate),
                "defrost": defrost,
                "heating1": int(heating),
                "igniOnDuration": duration,
                "ims": 0,
                "airTemp": {
                    "value": convert_set_temp_to_api_from_celsius_value(set_temp),
                    "unit": 0,
                    "hvacTempType": 0,
                },
            },
            "pin": pin,
        }

        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def start_climate_ev(
        self,
        access_token: str,
        vehicle_id: str,
        pin: str,
        set_temp,
        defrost,
        climate,
        heating,
        pin_token: str = None,
    ):
        url = self.api_url + "evc/rfon"

        json_body = {
            "hvacInfo": {
                "airCtrl": int(climate),
                "defrost": defrost,
                "heating1": int(heating),
                "airTemp": {
                    "value": convert_set_temp_to_api_from_celsius_value(set_temp),
                    "unit": 0,
                    "hvacTempType": 1,
                },
            },
            "pin": pin,
        }
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def stop_climate(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ):
        url = self.api_url + "rmtstp"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def stop_climate_ev(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ):
        url = self.api_url + "evc/rfoff"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def start_charge(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ):
        url = self.api_url + "evc/rcstrt"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]

    async def stop_charge(
        self, access_token: str, vehicle_id: str, pin: str, pin_token: str = None
    ):
        url = self.api_url + "evc/rcstp"
        json_body = {"pin": pin}
        response = await self._post_request_with_logging_and_errors_raised(
            access_token=access_token,
            vehicle_id=vehicle_id,
            url=url,
            pin_token=pin_token,
            json_body=json_body,
        )
        return response.headers["transactionId"]
