"""
<plugin key="RemehaHome" name="Remeha Home Plugin" author="Nick Baring" version="1.0.0">
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
import asyncio
from aiohttp import ClientSession

class RemehaHomeAPI:
    def __init__(self):
        self._session = ClientSession()
        self.email = ""
        self.password = ""
        
    def onStart(self):
        # Called when the plugin is started
        Domoticz.Log("Remeha Home Plugin started.")

        # Read options from Domoticz GUI
        self.readOptions()

        # Check if there are no existing devices
        if len(Devices) == 0:
            # Example: Create two normal Switch devices for controlling two bed sides
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
      
        # Retrieve the API key from Parameters if set, otherwise log an error
        if "Mode2" in Parameters and Parameters["Mode2"]:
            self.password = Parameters["Mode2"]
        else:
            Domoticz.Error("Password not configured in the Domoticz plugin configuration.")
    
    def createDevices(self):
        # Declare Devices variable
        global Devices

        # Example: Create a normal temperature device
        device_name_1 ="roomTemperature"  # Adjust the device name as needed
        device_id_1 = 1  # Adjust the device ID as needed

        # Create the device as a normal temperature device
        Domoticz.Device(Name=device_name_1, Unit=device_id_1, TypeName="Temperature", Used=1).Create()

        # Example: Create a normal temperature device
        device_name_2 = "outdoorTemperature"  # Adjust the device name as needed
        device_id_2 = 2  # Adjust the device ID as needed

        # Create the device as a normal temperature device
        Domoticz.Device(Name=device_name_2, Unit=device_id_2, TypeName="Temperature", Used=1).Create()
        
        # Example: Create a normal temperature device
        device_name_3 = "waterPressure"  # Adjust the device name as needed
        device_id_3 = 3  # Adjust the device ID as needed

        # Create the device as a normal temperature device
        Domoticz.Device(Name=device_name_3, Unit=device_id_3, TypeName="Pressure", Used=1).Create()

        

    async def async_resolve_external_data(self, email, password):
        random_state = secrets.token_urlsafe()
        code_challenge = secrets.token_urlsafe(64)
        code_challenge_sha256 = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_challenge.encode("ascii")).digest()
            )
            .decode("ascii")
            .rstrip("=")
        )

        response = await self._session.get(
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
            for cookie in self._session.cookie_jar
            if (
                cookie.key == "x-ms-cpim-csrf"
                and cookie["domain"] == "remehalogin.bdrthermea.net"
            )
        )

        response = await self._session.post(

            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/B2C_1A_RPSignUpSignInNewRoomv3.1/SelfAsserted",
            params={
                "tx": "StateProperties=" + state_properties,
                "p": "B2C_1A_RPSignUpSignInNewRoomv3.1",
            },
            headers={"x-csrf-token": csrf_token},
            data={
                "request_type": "RESPONSE",
                "signInName": email,
                "password": password,
            },
            
        )
        response.raise_for_status()
        response_json = json.loads(await response.text())
        if response_json["status"] != "200":
            Domoticz.Log(response_json["status"])

        response = await self._session.get(
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
        return await self._async_request_new_token(grant_params)

    async def _async_request_new_token(self, grant_params):
        async with self._session.post(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/oauth2/v2.0/token?p=B2C_1A_RPSignUpSignInNewRoomV3.1",
            data=grant_params,
            allow_redirects=True,
        ) as response:
            if response.status == 400:
                response_json = await response.json()
                print(
                    "OAuth2 token request returned '400 Bad Request': %s",
                    response_json["error_description"],
                )
            response.raise_for_status()
            response_json = await response.json()
                        

        return response_json

    async def _async_cleanup(self):
        await self._session.close()


    async def update_devices(self, access_token):
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Ocp-Apim-Subscription-Key": "df605c5470d846fc91e848b1cc653ddf",
        }

        try:
            async with self._session.get(
                "https://api.bdrthermea.net/Mobile/api/homes/dashboard", headers=headers
            ) as response:
                response.raise_for_status()

                response_json = await response.json()

                # Update Domoticz devices here based on the response_json
                valueRoomtemperature = response_json["appliances"][0]["climateZones"][0]["roomTemperature"]
                valueOutdoorTemperature = response_json["appliances"][0]["outdoorTemperature"]
                valueWaterPressure = response_json["appliances"][0]["waterPressure"]
                
                # Example: Update Domoticz devices
                if str(Devices[1].sValue) != str(valueRoomtemperature):
                    Devices[1].Update(nValue=0, sValue=str(valueRoomtemperature))
                if str(Devices[2].sValue) != str(valueOutdoorTemperature):
                    Devices[2].Update(nValue=0, sValue=str(valueOutdoorTemperature))
                if str(Devices[3].sValue) != str(valueWaterPressure):
                    Devices[3].Update(nValue=0, sValue=str(valueWaterPressure))
                

        except Exception as e:
            Domoticz.Error(f"Error making GET request: {e}")
        
    async def onheartbeat2(self):
        # Include your logic to request a new token here if needed

        remeha_api = RemehaHomeAPI()
        email = self.email
        password = self.password
        result = await remeha_api.async_resolve_external_data(email, password)
        access_token = result.get("access_token")
        await remeha_api.update_devices(access_token)
        await remeha_api._async_cleanup()


    def onheartbeat(self):
    # Include your logic to request a new token here if needed
        Domoticz.Log("Remeha Home plugin heartbeat")
        self.readOptions()
        asyncio.run(self.onheartbeat2())
        #asyncio.run(RemehaHomeAPI.onheartbeat2(self))
        #remeha_api = RemehaHomeAPI()
        #result = await remeha_api.async_resolve_external_data()
        #access_token = result.get("access_token")
        #await remeha_api.update_devices(access_token)
        #await remeha_api._async_cleanup()

# Create an instance of the Remehalugin class
_plugin = RemehaHomeAPI()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onHeartbeat():
    _plugin.onheartbeat()

def onConfigurationChanged():
    # Called when the plugin configuration is changed in Domoticz GUI
    _plugin.readOptions()
