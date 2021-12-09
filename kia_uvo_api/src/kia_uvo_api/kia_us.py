import logging

from datetime import datetime
import random
import string
import secrets

import pytz
import time

from aiohttp import ClientSession, ClientResponse, ClientError

from .auth_error import AuthError

_LOGGER = logging.getLogger(__name__)


def request_with_logging(func):
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
        if response_json["status"]["statusCode"] == 0:
            return response
        if (
            response_json["status"]["statusCode"] == 1
            and response_json["status"]["errorType"] == 1
            and (
                response_json["status"]["errorCode"] == 1003
                or response_json["status"]["errorCode"] == 1037
                or response_json["status"]["errorCode"] == 1001
            )
        ):
            _LOGGER.debug(f"error: session invalid")
            raise AuthError
        response_text = await response.text()
        _LOGGER.error(f"error: unknown error response {response_text}")
        raise ClientError

    return request_with_logging_wrapper


class KiaUs:
    def __init__(self):
        # Randomly generate a plausible device id on startup
        self.device_id = (
            "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(22)
            )
            + ":"
            + secrets.token_urlsafe(105)
        )

        self.BASE_URL: str = "api.owners.kia.com"
        self.API_URL: str = "https://" + self.BASE_URL + "/apigw/v1/"

        self.api_session = ClientSession(raise_for_status=True)

    async def close(self):
        await self.api_session.close()

    def _api_headers(self, session_id: str = None, vehicle_key: str = None) -> dict:
        headers = {
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "apptype": "L",
            "appversion": "4.10.0",
            "clientid": "MWAMOBILE",
            "from": "SPA",
            "host": self.BASE_URL,
            "language": "0",
            "offset": str(int(time.localtime().tm_gmtoff / 60 / 60)),
            "ostype": "Android",
            "osversion": "11",
            "secretkey": "98er-w34rf-ibf3-3f6h",
            "to": "APIGW",
            "tokentype": "G",
            "user-agent": "okhttp/3.12.1",
            "deviceid": self.device_id,
            "date": datetime.now(tz=pytz.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        if session_id is not None:
            headers["sid"] = session_id
        if vehicle_key is not None:
            headers["vinkey"] = vehicle_key
        return headers

    @request_with_logging
    async def _post_request_with_logging_and_active_session(
        self, session_id: str, vehicle_key: str, url: str, json_body: dict
    ) -> ClientResponse:
        headers = self._api_headers(session_id, vehicle_key)
        return await self.api_session.post(url=url, json=json_body, headers=headers)

    @request_with_logging
    async def _get_request_with_logging_and_active_session(
        self, session_id: str, vehicle_key: str, url: str
    ) -> ClientResponse:
        headers = self._api_headers(session_id, vehicle_key)
        return await self.api_session.get(url=url, headers=headers)

    async def login(self, username: str, password: str) -> str:
        url = self.API_URL + "prof/authUser"

        data = {
            "deviceKey": "",
            "deviceType": 2,
            "userCredential": {"userId": username, "password": password},
        }
        response: ClientResponse = (
            await self._post_request_with_logging_and_active_session(
                session_id=None, vehicle_key=None, url=url, json_body=data
            )
        )
        session_id = response.headers.get("sid")
        if not session_id:
            response_text = await response.text()
            raise Exception(
                f"no session id returned in login. Response: {response_text} headers {response.headers} cookies {response.cookies}"
            )
        _LOGGER.debug(f"got session id {session_id}")
        return session_id

    async def get_vehicles(self, session_id: str):
        """
        {"status":{"statusCode":0,"errorType":0,"errorCode":0,"errorMessage":"Success with response body"},"payload":{"vehicleSummary":[{"vin":"VIN","vehicleIdentifier":"1234","modelName":"NIRO EV","modelYear":"2019","nickName":"Niro EV","generation":2,"extColorCode":"C3S","trim":"EX PREMIUM","imagePath":{"imageName":"2019-niro_ev-ex_premium-c3s.png","imagePath":"/content/dam/kia/us/owners/image/vehicle/2019/niro_ev/ex_premium/","imageType":"1","imageSize":{"length":"100","width":"100","uom":0}},"enrollmentStatus":1,"fatcAvailable":1,"telematicsUnit":1,"fuelType":4,"colorName":"ALUMINUM SILVER","activationType":2,"mileage":"12844.7","dealerCode":"MD047","mobileStore":[{"osType":0,"downloadURL":"https://itunes.apple.com/us/app/kia-access-with-uvo-link/id1280548773?mt=8","image":{"imageName":"iosImage.png","imagePath":"/content/dam/kia/us/owners/image/common/app/","imageType":"2","imageSize":{"length":"100","width":"100","uom":0}}},{"osType":1,"downloadURL":"https://play.google.com/store/apps/details?id=com.myuvo.link","image":{"imageName":"androidImage.png","imagePath":"/content/dam/kia/us/owners/image/common/app/","imageType":"2","imageSize":{"length":"100","width":"100","uom":0}}}],"supportedApp":{"appType":"5","appImage":{"imageName":"uvo-app.png","imagePath":"/content/dam/kia/us/owners/image/common/app/access/","imageType":"2","imageSize":{"length":"100","width":"100","uom":0}}},"supportAdditionalDriver":0,"customerType":0,"projectCode":"DEEV","headUnitDesc":"AVN5.0","provStatus":"4","enrollmentSuppressionType":0,"vehicleKey":"KEY"}]}}
        """
        url = self.API_URL + "ownr/gvl"
        response: ClientResponse = (
            await self._get_request_with_logging_and_active_session(
                session_id=session_id, vehicle_key=None, url=url
            )
        )
        response_json = await response.json()
        return response_json["payload"]

    async def get_cached_vehicle_status(self, session_id: str, vehicle_key: str):
        """
        {"status":{"statusCode":0,"errorType":0,"errorCode":0,"errorMessage":"Success with response body"},"payload":{"vehicleInfoList":[{"vinKey":"KEY","vehicleConfig":{"vehicleDetail":{"vehicle":{"vin":"VIN","trim":{"modelYear":"2019","salesModelCode":"V1262","optionGroupCode":"015","modelName":"NIRO EV","factoryCode":"DQ","projectCode":"DEEV","trimName":"EX PREMIUM","driveType":"0","transmissionType":"1","ivrCategory":"6","btSeriesCode":"N"},"telematics":1,"mileage":"12844.7","mileageSyncDate":"20211130003749","exteriorColor":"ALUMINUM SILVER","exteriorColorCode":"C3S","fuelType":4,"invDealerCode":"CODE","testVehicle":"0","supportedApps":[{"appType":"0"},{"appType":"5","appImage":{"imageName":"uvo-app.png","imagePath":"/content/dam/kia/us/owners/image/common/app/access/","imageType":"2","imageSize":{"length":"100","width":"100","uom":0}}}],"activationType":2},"images":[{"imageName":"2019-niro_ev-ex_premium-c3s.png","imagePath":"/content/dam/kia/us/owners/image/vehicle/2019/niro_ev/ex_premium/","imageType":"1","imageSize":{"length":"100","width":"100","uom":0}}],"device":{"launchType":"0","swVersion":"DEEV.USA.SOP.V105.190503.STD_H","telematics":{"generation":"3","platform":"1","tmsCenter":"1","billing":true},"versionNum":"ECO","headUnitType":"0","hdRadio":"X40HA","ampType":"NA","modem":{"meid":"354522081158920","mdn":"6573652075","iccid":"89148000005051202869"},"headUnitName":"avn40ev_np","bluetoothRef":"10","headUnitDesc":"AVN5.0"}},"billingPeriod":{"freeTrial":{"value":12,"unit":0},"freeTrialExtension":{"value":12,"unit":1},"servicePeriod":{"value":60,"unit":1}}},"lastVehicleInfo":{"vehicleNickName":"Niro EV","preferredDealer":"CODE","customerType":0,"enrollment":{"provStatus":"4","enrollmentStatus":"1","enrollmentType":"0","registrationDate":"20191123","expirationDate":"20201122","expirationMileage":"100000","freeServiceDate":{"startDate":"20191122","endDate":"20201122"}},"activeDTC":{"dtcActiveCount":"0"},"vehicleStatusRpt":{"statusType":"2","reportDate":{"utc":"20211130170553","offset":-8},"vehicleStatus":{"climate":{"airCtrl":false,"defrost":false,"airTemp":{"value":"72","unit":1},"heatingAccessory":{"steeringWheel":0,"sideMirror":0,"rearWindow":0}},"engine":false,"doorLock":true,"doorStatus":{"frontLeft":0,"frontRight":0,"backLeft":0,"backRight":0,"trunk":0,"hood":0},"lowFuelLight":false,"evStatus":{"batteryCharge":false,"batteryStatus":79,"batteryPlugin":0,"remainChargeTime":[{"remainChargeType":1,"timeInterval":{"value":0,"unit":4}},{"remainChargeType":2,"timeInterval":{"value":0,"unit":4}},{"remainChargeType":3,"timeInterval":{"value":0,"unit":4}}],"drvDistance":[{"type":2,"rangeByFuel":{"evModeRange":{"value":213,"unit":3},"totalAvailableRange":{"value":213,"unit":3}}}],"syncDate":{"utc":"20211130165836","offset":-8},"targetSOC":[{"plugType":0,"targetSOClevel":80,"dte":{"type":2,"rangeByFuel":{"gasModeRange":{"value":0,"unit":3},"evModeRange":{"value":213,"unit":3},"totalAvailableRange":{"value":213,"unit":3}}}},{"plugType":1,"targetSOClevel":90,"dte":{"type":2,"rangeByFuel":{"gasModeRange":{"value":0,"unit":3},"evModeRange":{"value":213,"unit":3},"totalAvailableRange":{"value":213,"unit":3}}}}]},"ign3":true,"transCond":true,"tirePressure":{"all":0},"dateTime":{"utc":"20211130170553","offset":-8},"syncDate":{"utc":"20211130165836","offset":-8},"batteryStatus":{"stateOfCharge":87,"sensorStatus":0},"sleepMode":false,"lampWireStatus":{"headLamp":{},"stopLamp":{},"turnSignalLamp":{}},"windowStatus":{},"engineRuntime":{},"valetParkingMode":0}},"location":{"coord":{"lat":20.2,"lon":-7.9,"alt":119,"type":0,"altdo":0},"head":347,"speed":{"value":0,"unit":1},"accuracy":{"hdop":7,"pdop":12},"syncDate":{"utc":"20211130153749","offset":-8}},"financed":true,"financeRegistered":true,"linkStatus":0}}]}}
        """
        url = self.API_URL + "cmm/gvi"

        body = {
            "vehicleConfigReq": {
                "airTempRange": "0",
                "maintenance": "0",
                "seatHeatCoolOption": "0",
                "vehicle": "1",
                "vehicleFeature": "0",
            },
            "vehicleInfoReq": {
                "drivingActivty": "0",
                "dtc": "1",
                "enrollment": "1",
                "functionalCards": "0",
                "location": "1",
                "vehicleStatus": "1",
                "weather": "0",
            },
            "vinKey": [vehicle_key],
        }
        response = await self._post_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url, json_body=body
        )

        response_json = await response.json()
        return response_json["payload"]

    async def request_vehicle_data_sync(self, session_id: str, vehicle_key: str):
        """
        {"status":{"statusCode":0,"errorType":0,"errorCode":0,"errorMessage":"Success with response body"},"payload":{"vehicleStatusRpt":{"statusType":"1","reportDate":{"utc":"20211130173341","offset":-8},"vehicleStatus":{"climate":{"airCtrl":false,"defrost":false,"airTemp":{"value":"72","unit":1},"heatingAccessory":{"steeringWheel":0,"sideMirror":0,"rearWindow":0}},"engine":false,"doorLock":true,"doorStatus":{"frontLeft":0,"frontRight":0,"backLeft":0,"backRight":0,"trunk":0,"hood":0},"lowFuelLight":false,"evStatus":{"batteryCharge":false,"batteryStatus":79,"batteryPlugin":0,"remainChargeTime":[{"remainChargeType":1,"timeInterval":{"value":0,"unit":4}},{"remainChargeType":2,"timeInterval":{"value":0,"unit":4}},{"remainChargeType":3,"timeInterval":{"value":0,"unit":4}}],"drvDistance":[{"type":2,"rangeByFuel":{"evModeRange":{"value":213,"unit":3},"totalAvailableRange":{"value":213,"unit":3}}}],"syncDate":{"utc":"20211130165836","offset":-8},"targetSOC":[{"plugType":0,"targetSOClevel":80,"dte":{"type":2,"rangeByFuel":{"gasModeRange":{"value":0,"unit":3},"evModeRange":{"value":213,"unit":3},"totalAvailableRange":{"value":213,"unit":3}}}},{"plugType":1,"targetSOClevel":90,"dte":{"type":2,"rangeByFuel":{"gasModeRange":{"value":0,"unit":3},"evModeRange":{"value":213,"unit":3},"totalAvailableRange":{"value":213,"unit":3}}}}]},"ign3":true,"transCond":true,"tirePressure":{"all":0},"dateTime":{"utc":"20211130173341","offset":-8},"syncDate":{"utc":"20211130165836","offset":-8},"batteryStatus":{"stateOfCharge":87,"sensorStatus":0},"sleepMode":false,"lampWireStatus":{"headLamp":{},"stopLamp":{},"turnSignalLamp":{}},"windowStatus":{},"engineRuntime":{},"valetParkingMode":0}}}}
        """
        url = self.API_URL + "rems/rvs"
        body = {
            "requestType": 0  # value of 1 would return cached results instead of forcing update
        }
        await self._post_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url, json_body=body
        )

    async def check_last_action_status(
        self, session_id: str, vehicle_key: str, xid: str
    ):
        url = self.API_URL + "cmm/gts"
        body = {"xid": xid}
        response = await self._post_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url, json_body=body
        )
        response_json = await response.json()
        return all(v == 0 for v in response_json["payload"].values())

    async def lock(self, session_id: str, vehicle_key: str):
        url = self.API_URL + "rems/door/lock"
        response = await self._get_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url
        )
        return response.headers["Xid"]

    async def unlock(self, session_id: str, vehicle_key: str):
        url = self.API_URL + "rems/door/unlock"
        response = await self._get_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url
        )
        return response.headers["Xid"]

    async def start_climate(
        self, session_id: str, vehicle_key: str, set_temp, defrost, climate, heating
    ):
        url = self.API_URL + "rems/start"
        body = {
            "remoteClimate": {
                "airCtrl": climate,
                "airTemp": {
                    "unit": 1,
                    "value": str(set_temp),
                },
                "defrost": defrost,
                "heatingAccessory": {
                    "rearWindow": int(heating),
                    "sideMirror": int(heating),
                    "steeringWheel": int(heating),
                },
                "ignitionOnDuration": {
                    "unit": 4,
                    "value": 9,
                },
            }
        }
        response = await self._post_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url, json_body=body
        )
        return response.headers["Xid"]

    async def stop_climate(self, session_id: str, vehicle_key: str):
        url = self.API_URL + "rems/stop"
        response = await self._get_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url
        )
        return response.headers["Xid"]

    async def start_charge(self, session_id: str, vehicle_key: str):
        url = self.API_URL + "evc/charge"
        body = {"chargeRatio": 100}
        response = await self._post_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url, json_body=body
        )
        return response.headers["Xid"]

    async def stop_charge(self, session_id: str, vehicle_key: str):
        url = self.API_URL + "evc/cancel"
        response = await self._get_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url
        )
        return response.headers["Xid"]

    async def set_charge_limits(
        self, session_id: str, vehicle_key: str, ac_limit: int, dc_limit: int
    ):
        url = self.API_URL + "evc/sts"
        body = {
            "targetSOClist": [
                {
                    "plugType": 0,
                    "targetSOClevel": dc_limit,
                },
                {
                    "plugType": 1,
                    "targetSOClevel": ac_limit,
                },
            ]
        }
        response = await self._post_request_with_logging_and_active_session(
            session_id=session_id, vehicle_key=vehicle_key, url=url, json_body=body
        )
        return response.headers["Xid"]
