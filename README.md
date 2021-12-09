[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A custom integration for Kia Uvo USA region. This project was mostly inspired by this [home assistant integration](https://github.com/fuatakgun/kia_uvo)

Warning ahead; this is pre-alpha phase, please do not expect something fully functional, I will improve the integration by time.

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing!). 

- It will only fetch values for the first car, I am sure there are people outside using Kia Uvo with multiple cars, please create an issue, so I can gauge interest.
- refresh - It will fetch the cached information every 30 minutes from Kia Uvo Servers. **Now Configurable**
- request sync - It will ask your car for the latest data every 4 hours. **Now Configurable**
- It will not force update between 6PM to 6AM. I am trying to be cautious here. **Now Configurable**
- To setup two vehicles add the integration through HA UI twice.

## Supported entities ##
- Air Conditioner Status, Defroster Status, Set Temperature
- Heated Rear Window, Heated Steering Wheel
- Car Battery Level (12v), EV Battery Level, Remaining Time to Full Charge
- Tire Pressure Warnings (all)
- Charge Status and Plugged In Status
- Low Fuel Light Status
- Doors, Trunk and Hood Open/Close Status
- Locking and Unlocking
- Engine Status
- Odometer, EV Range
- Last Updated from Cloud: Timestamp this integration last attempted to retrieve data from the cloud
- Sync Age: Minutes since car synced to cloud during last update

## Supported services ##
- update: get latest **cached** vehicle data
- request_sync: this will make a call to your vehicle to get its latest data, do not overuse this!
- start_climate / stop_climate: Control the HVAC car services
- start_charge / stop_charge: You can control your charging using these services
- set_charge_limits: You can control your charging capacity limits using this services

## Troubleshooting ##
If you receive an error while trying to login, please go through these steps;
1. You can enable logging for this integration specifically and share your logs, so I can have a deep dive investigation. To enable logging, update your `configuration.yaml` like this, we can get more information in Configuration -> Logs page
```
logger:
  default: warning
  logs:
    custom_components.kia_uvo: debug
```

