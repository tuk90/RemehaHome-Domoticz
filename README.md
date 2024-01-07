# Remeha Home Plugin for Domoticz

## Description
This Domoticz Python plugin allows you to integrate Remeha Home devices into your Domoticz home automation system.

## Installation

1. Download the plugin files to your Domoticz plugins directory.
2. Restart Domoticz.

## Configuration

1. Open the Domoticz web interface.
2. Navigate to "Setup" -> "Hardware."
3. Add a new hardware device with the type "Remeha Home Plugin."
4. Enter your Remeha Home account credentials (email and password) in the configuration settings.

## Devices

The plugin creates the following devices by default:

1. Room Temperature Sensor
2. Outdoor Temperature Sensor
3. Water Pressure Sensor

These devices are used to display information from the Remeha Home API.

## Usage

Once the plugin is configured and devices are created, it will automatically fetch data from the Remeha Home API at regular intervals (heartbeats) and update the corresponding Domoticz devices.

## Important Notes

- Ensure that your Domoticz server has internet access to communicate with the Remeha Home API.
- The plugin uses asyncio and aiohttp libraries for asynchronous requests. Make sure your Domoticz environment supports these.

## Credits
This plugin is based on the [Remeha Home Python library](https://github.com/msvisser/remeha_home) by Michiel Visser.
