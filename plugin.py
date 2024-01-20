"""
<plugin key="RemehaHome" name="Remeha Home Plugin" author="Nick Baring" version="0.0.3">
    <params>
        <param field="Mode1" label="Email" width="200px" required="true"/>
        <param field="Mode2" label="Password" width="200px" password="true" required="true"/>
    </params>
</plugin>
"""
import Domoticz
import base64
import hashlib
import json
import urllib
import secrets
import requests
import datetime

class RemehaHomeAPI:
    def __init__(self):
        # Initialize a session for making HTTP requests
        self._session = requests.Session()
        self.email = ""
        self.password = ""

    def onStart(self):
        # Called when the plugin is started
        Domoticz.Log("Remeha Home Plugin started.")
        # Read options from Domoticz GUI
        self.readOptions()
        # Check if there are no existing devices
        if len(Devices) != 5:
            # Example: Create devices for temperature, pressure, and setpoint
            self.createDevices()
        else:
            Domoticz.Log("Devices already exist. Skipping device creation.")
        Domoticz.Heartbeat(30)

    def onStop(self):
        # Called when the plugin is stopped
        Domoticz.Log("Remeha Home Plugin stopped.")

    def readOptions(self):
        # Read options from Domoticz GUI
        if Parameters["Mode1"]:
            self.email = Parameters["Mode1"]
        if "Mode2" in Parameters and Parameters["Mode2"]:
            self.password = Parameters["Mode2"]
        else:
            Domoticz.Error("Password not configured in the Domoticz plugin configuration.")

    def createDevices(self):
        # Declare Devices variable
        global Devices

        # Create devices for temperature, pressure, and setpoint
        device_name_1 = "roomTemperature"
        device_id_1 = 1
        Domoticz.Device(Name=device_name_1, Unit=device_id_1, TypeName="Temperature", Used=1).Create()

        device_name_2 = "outdoorTemperature"
        device_id_2 = 2
        Domoticz.Device(Name=device_name_2, Unit=device_id_2, TypeName="Temperature", Used=1).Create()

        device_name_3 = "waterPressure"
        device_id_3 = 3
        Domoticz.Device(Name=device_name_3, Unit=device_id_3, TypeName="Pressure", Used=1).Create()

        device_name_4 = "setPoint"
        device_id_4 = 4
        Domoticz.Device(Name=device_name_4, Unit=device_id_4, TypeName="Setpoint", Used=1).Create()
        
        device_name_5 = "EnergyConsumption"
        device_id_5 = 5
        Domoticz.Device(Name=device_name_5, Unit=device_id_5, Type=113, TypeName="Counter", Subtype=0, Switchtype=0, Used=1).Create()

    def resolve_external_data(self):
        # Logic for resolving external data (OAuth2 flow)
        random_state = secrets.token_urlsafe()
        code_challenge = secrets.token_urlsafe(64)
        code_challenge_sha256 = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_challenge.encode("ascii")).digest()
            )
            .decode("ascii")
            .rstrip("=")
        )

        response = self._session.get(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/oauth2/v2.0/authorize",
            params={
                "response_type": "code",
                "client_id": "6ce007c6-0628-419e-88f4-bee2e6418eec",
                "redirect_uri": "com.b2c.remehaapp://login-callback",
                "scope": "openid https://bdrb2cprod.onmicrosoft.com/iotdevice/user_impersonation offline_access",
                "state": random_state,
                "code_challenge": code_challenge_sha256,
                "code_challenge_method": "S256",
                "p": "B2C_1A_RPSignUpSignInNewRoomV3.1",
                "brand": "remeha",
                "lang": "en",
                "nonce": "defaultNonce",
                "prompt": "login",
                "signUp": "False",
            },
        )
        response.raise_for_status()

        request_id = response.headers["x-request-id"]
        state_properties_json = f'{{"TID":"{request_id}"}}'.encode("ascii")
        state_properties = (
            base64.urlsafe_b64encode(state_properties_json)
            .decode("ascii")
            .rstrip("=")
        )

        csrf_token = next(
            cookie.value
            for cookie in self._session.cookies
            if (
                cookie.name == "x-ms-cpim-csrf"
                and cookie.domain == ".remehalogin.bdrthermea.net"
            )
        )

        response = self._session.post(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/B2C_1A_RPSignUpSignInNewRoomv3.1/SelfAsserted",
            params={
                "tx": "StateProperties=" + state_properties,
                "p": "B2C_1A_RPSignUpSignInNewRoomv3.1",
            },
            headers={"x-csrf-token": csrf_token},
            data={
                "request_type": "RESPONSE",
                "signInName": self.email,
                "password": self.password,
            },
        )
        response.raise_for_status()
        response_json = json.loads(response.text)
        if response_json["status"] != "200":
            Domoticz.Log(response_json["status"])

        response = self._session.get(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/B2C_1A_RPSignUpSignInNewRoomv3.1/api/CombinedSigninAndSignup/confirmed",
            params={
                "rememberMe": "false",
                "csrf_token": csrf_token,
                "tx": "StateProperties=" + state_properties,
                "p": "B2C_1A_RPSignUpSignInNewRoomv3.1",
            },
            allow_redirects=False,
        )
        response.raise_for_status()

        parsed_callback_url = urllib.parse.urlparse(response.headers["location"])
        query_string_dict = urllib.parse.parse_qs(parsed_callback_url.query)
        authorization_code = query_string_dict["code"]

        grant_params = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": "com.b2c.remehaapp://login-callback",
            "code_verifier": code_challenge,
            "client_id": "6ce007c6-0628-419e-88f4-bee2e6418eec",
        }
        return self._request_new_token(grant_params)

    def _request_new_token(self, grant_params):
        # Logic for requesting a new access token
        with self._session.post(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/oauth2/v2.0/token?p=B2C_1A_RPSignUpSignInNewRoomV3.1",
            data=grant_params,
            allow_redirects=True,
        ) as response:
            if response.status_code == 400:
                response_json = response.json()
                Domoticz.Log(
                    "OAuth2 token request returned '400 Bad Request': %s",
                    response_json["error_description"],
                )
            response.raise_for_status()
            response_json = response.json()
        return response_json

    def cleanup(self):
        # Cleanup session resources
        self._session.close()

    def update_devices(self, access_token):
        # Update Domoticz devices with data from Remeha Home
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Ocp-Apim-Subscription-Key": "df605c5470d846fc91e848b1cc653ddf",
        }

        try:
            response = self._session.get(
                "https://api.bdrthermea.net/Mobile/api/homes/dashboard", headers=headers
            )
            response.raise_for_status()

            response_json = response.json()
            
            # Update Domoticz devices here based on the response_json
            value_room_temperature = response_json["appliances"][0]["climateZones"][0]["roomTemperature"]
            value_outdoor_temperature = response_json["appliances"][0]["outdoorTemperature"]
            if value_outdoor_temperature is None:
                # No real outdoor temperature device, using cloud value
                value_outdoor_temperature = response_json["appliances"][0]["outdoorTemperatureInformation"]["cloudOutdoorTemperature"]
            value_water_pressure = response_json["appliances"][0]["waterPressure"]
            value_setpoint = response_json["appliances"][0]["climateZones"][0]["setPoint"]

            if str(Devices[1].sValue) != str(value_room_temperature):
                Devices[1].Update(nValue=0, sValue=str(value_room_temperature))
            if str(Devices[2].sValue) != str(value_outdoor_temperature):
                Devices[2].Update(nValue=0, sValue=str(value_outdoor_temperature))
            if str(Devices[3].sValue) != str(value_water_pressure):
                Devices[3].Update(nValue=0, sValue=str(value_water_pressure))
            if str(Devices[4].sValue) != str(value_setpoint):
                Devices[4].Update(nValue=0, sValue=str(value_setpoint))

        except Exception as e:
            Domoticz.Error(f"Error making GET request: {e}")

    def set_temperature(self, access_token, room_temperature_setpoint):
        # Set temperature in the external system using a POST request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Ocp-Apim-Subscription-Key': 'df605c5470d846fc91e848b1cc653ddf'
        }

        try:
            response = self._session.get(
                'https://api.bdrthermea.net/Mobile/api/homes/dashboard',
                headers=headers
            )
            response.raise_for_status()

            response_json = response.json()
            climate_zone_id = response_json["appliances"][0]["climateZones"][0]["climateZoneId"]

        except Exception as e:
            Domoticz.Error(f"Error making GET request: {e}")

        try:
            json_data = {'roomTemperatureSetPoint': room_temperature_setpoint}
            response = self._session.post(
                f'https://api.bdrthermea.net/Mobile/api/climate-zones/{climate_zone_id}/modes/temporary-override',
                headers=headers,
                json=json_data
            )
            response.raise_for_status()
            Domoticz.Log(f"Temperature set successfully to {room_temperature_setpoint}")
        except Exception as e:
            Domoticz.Error(f"Error making POST request: {e}")
    def getDailyEnergyConsumption(self, access_token):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Ocp-Apim-Subscription-Key': 'df605c5470d846fc91e848b1cc653ddf'
            }
        try:
            response = requests.get(
            'https://api.bdrthermea.net/Mobile/api/homes/dashboard',
            headers=headers
        )
            response.raise_for_status()
            # Do something with the response if needed
            response_json = response.json()
        except Exception as e:
            print(f"Error making GET request: {e}")
        
        appliance_id = response_json["appliances"][0]["applianceId"]
        
        current_year = datetime.datetime.now().year
        next_year = current_year + 1
    
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = today + datetime.timedelta(hours=23, minutes=59, seconds=59)

        today_string = today.strftime("%Y-%m-%d %H:%M:%S.%fZ")
        end_of_today_string = end_of_today.strftime("%Y-%m-%d %H:%M:%S.%fZ")
    
        try:
            response = requests.get(
                f'https://api.bdrthermea.net/Mobile/api/appliances/{appliance_id}/energyconsumption/yearly?startDate=1900-01-01 00:00:00.000Z&endDate={next_year}-01-01 00:00:00.000Z',
                headers=headers
            )
            response_json = response.json()
            
            # Initialize a variable to store the sum
            total_heating_energy_consumed = 0
            
            #sums up all the year results to get the total energycounter
            for entry in response_json["data"]:
                total_heating_energy_consumed += entry["heatingEnergyConsumed"]
            
            #EnergyConsumed = response_json["data"][0]["heatingEnergyConsumed"]
            total_heating_energy_consumed = total_heating_energy_consumed * 1000            
            if str(Devices[5].sValue) != str(total_heating_energy_consumed):
                Devices[5].Update(nValue=0, sValue=str(total_heating_energy_consumed))
        except Exception as e:
            print(f"Error making GET request: {e}")


    def onheartbeat(self):
        # Heartbeat function called periodically
        Domoticz.Log("Remeha Home plugin heartbeat")
        result = self.resolve_external_data()
        access_token = result.get("access_token")
        self.update_devices(access_token)
        self.getDailyEnergyConsumption(access_token)
        self.cleanup()

    def oncommand(self, unit, command, level, hue):
        # Command handling function
        if unit == 4:  # setpoint device
            if command == 'Set Level':
                room_temperature_setpoint = float(level)
        result = self.resolve_external_data()
        access_token = result.get("access_token")
        self.set_temperature(access_token, room_temperature_setpoint)
        self.cleanup()

# Create an instance of the RemehaHomeAPI class
_plugin = RemehaHomeAPI()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onHeartbeat():
    _plugin.onheartbeat()

def onCommand(unit, command, level, hue):
    _plugin.oncommand(unit, command, level, hue)

def onConfigurationChanged():
    _plugin.readOptions()
