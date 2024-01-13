import base64
import hashlib
import json
import logging
import secrets
import urllib
import requests

class RemehaHomeAPI:
    """Provide Remeha Home authentication tied to an OAuth2 based config entry."""

    def __init__(self):
        """Initialize Remeha Home auth."""
        self._session = requests.Session()

    def resolve_external_data(self, email, password) -> dict:
        """Resolve external data to tokens."""
        email = email
        password = password

        # Generate a random state and code challenge
        random_state = secrets.token_urlsafe()
        code_challenge = secrets.token_urlsafe(64)
        code_challenge_sha256 = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_challenge.encode("ascii")).digest()
            )
            .decode("ascii")
            .rstrip("=")
        )

        # Request the login page starting a new login transaction
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

        # Find the request id from the headers and package it up in base64 encoded json
        request_id = response.headers["x-request-id"]
        state_properties_json = f'{{"TID":"{request_id}"}}'.encode("ascii")
        state_properties = (
            base64.urlsafe_b64encode(state_properties_json)
            .decode("ascii")
            .rstrip("=")
        )

        # Find the CSRF token in the "x-ms-cpim-csrf" header
        csrf_token = next(
            cookie.value
            for cookie in self._session.cookies
            if (
                cookie.name == "x-ms-cpim-csrf"
                and cookie.domain == ".remehalogin.bdrthermea.net"
            )
        )

        # Post the user credentials to authenticate
        response = self._session.post(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/B2C_1A_RPSignUpSignInNewRoomv3.1/SelfAsserted",
            params={
                "tx": "StateProperties=" + state_properties,
                "p": "B2C_1A_RPSignUpSignInNewRoomv3.1",
            },
            headers={
                "x-csrf-token": csrf_token,
            },
            data={
                "request_type": "RESPONSE",
                "signInName": email,
                "password": password,
            },
        )
        response.raise_for_status()
        response_json = json.loads(response.text)
        print(response_json)
        if response_json["status"] != "200":
            raise RemehaHomeAuthFailed

        # Request the authentication complete callback
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

        # Parse the callback url for the authorization code
        parsed_callback_url = urllib.parse.urlparse(response.headers["location"])
        query_string_dict = urllib.parse.parse_qs(parsed_callback_url.query)
        authorization_code = query_string_dict["code"]

        # Request a new token with the authorization code
        grant_params = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": "com.b2c.remehaapp://login-callback",
            "code_verifier": code_challenge,
            "client_id": "6ce007c6-0628-419e-88f4-bee2e6418eec",
        }
        return self._request_new_token(grant_params)

    def _request_new_token(self, grant_params):
        """Call the OAuth2 token endpoint with specific grant parameters."""
        with self._session.post(
            "https://remehalogin.bdrthermea.net/bdrb2cprod.onmicrosoft.com/oauth2/v2.0/token?p=B2C_1A_RPSignUpSignInNewRoomV3.1",
            data=grant_params,
            allow_redirects=True,
        ) as response:
            # NOTE: The OAuth2 token request sometimes returns a "400 Bad Request" response. The root cause of this
            #       problem has not been found, but this workaround allows you to reauthenticate at least. Otherwise
            #       Home Assistant would get stuck on refreshing the token forever.
            if response.status_code == 400:
                response_json = response.json()
                print(
                    "OAuth2 token request returned '400 Bad Request': %s",
                    response_json["error_description"],
                )

            response.raise_for_status()
            response_json = response.json()
            return response_json

    def cleanup(self):
        # Cleanup resources, close the session, etc.
        self._session.close()

def main(email, password):
    remeha_api = RemehaHomeAPI()
    result = remeha_api.resolve_external_data(email, password)
    access_token = result.get('access_token')
    setScheduleMode(access_token)
    remeha_api.cleanup()

def GetTempValues(access_token):
    # Include your logic to request a new token here if needed

    # Example: Make a GET request using the obtained access token
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
        print(response_json)
        return response_json
    except Exception as e:
        print(f"Error making GET request: {e}")

def setTemperature(access_token):
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
        climateZoneId = response_json["appliances"][0]["climateZones"][0]["climateZoneId"]
        zoneMode = response_json["appliances"][0]["climateZones"][0]["zoneMode"]
        valueSetpoint = response_json["appliances"][0]["climateZones"][0]["setPoint"]
        print(zoneMode)
        print(valueSetpoint)
    except Exception as e:
        print(f"Error making GET request: {e}")

    try:
        json_data = {'roomTemperatureSetPoint': 20}
        response = requests.post(
            f'https://api.bdrthermea.net/Mobile/api/climate-zones/{climateZoneId}/modes/manual',
            headers=headers,
            json=json_data
        )
    except Exception as e:
        print(f"Error making POST request: {e}")

def setScheduleMode(access_token):
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
        climateZoneId = response_json["appliances"][0]["climateZones"][0]["climateZoneId"]
        valueSetpoint = response_json["appliances"][0]["climateZones"][0]["setPoint"]
        zoneMode = response_json["appliances"][0]["climateZones"][0]["zoneMode"]
        print(zoneMode)
        print(valueSetpoint)

    except Exception as e:
        print(f"Error making GET request: {e}")

    try:
        json_data = {'heatingProgramId': 1}
        response = requests.post(
            f'https://api.bdrthermea.net/Mobile/api/climate-zones/{climateZoneId}/modes/schedule',
            headers=headers,
            json=json_data
        )
    except Exception as e:
        print(f"Error making POST request: {e}")

# Run the main function
email = ""
password = ""
main(email, password)
