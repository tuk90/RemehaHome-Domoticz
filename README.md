# Remeha Home Plugin for Domoticz

## Overview
This Domoticz Python plugin integrates with the Remeha Home API, providing real-time information about your heating system. It creates Domoticz devices for temperature, pressure, and setpoint control.

## Credits
This plugin is based on the Remeha Home Python library by Michiel Visser, available at [GitHub - Remeha Home Library](https://github.com/msvisser/remeha_home).

## Installation
1. Clone this repository into the Domoticz plugins folder using the following command: git clone https://github.com/tuk90/RemehaHome-Domoticz.git
2. Restart the Domoticz service.
3. Go to the Domoticz web interface, navigate to "Hardware," and add a new hardware device with type "Remeha Home Plugin."

## Plugin Parameters
- **Email:** Your Remeha Home account email.
- **Password:** Your Remeha Home account password.

## Devices
The plugin creates the following devices in Domoticz:
1. Room Temperature
2. Outdoor Temperature
3. Water Pressure
4. Setpoint

## Usage
The plugin fetches data from the Remeha Home API and updates the corresponding Domoticz devices. Additionally, you can set the temperature setpoint using the "Setpoint" device.

## Support
For any issues or questions, please open an issue on the [GitHub repository](https://github.com/tuk90/RemehaHome-Domoticz).
