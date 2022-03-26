from urequests import request
from models import LightState
import secrets
import ujson

def fetch_state():
    response = request("GET", secrets.api_endpoint + "states/light.elgato_szymon_s_desk", headers={
        "Authorization": "Bearer " + secrets.api_token,
    })

    if (response.status_code > 200):
        print("Failed to fetch recent state, error code: " + str(response.status_code))
        return None
    response_state = response.json()
    light_state = LightState(
        state=response_state["state"] == 'on',
        brightness = response_state["attributes"]["brightness"] if "brightness" in response_state["attributes"] else 100,
        color_temp = response_state["attributes"]["color_temp"] if "color_temp" in response_state["attributes"] else 300,
    )
    return light_state

def update_state(state):
    data = {"entity_id": "light.elgato_szymon_s_desk"} if not state.state else {
        "entity_id": "light.elgato_szymon_s_desk",
        "brightness": state.brightness.value,
        "color_temp": state.color_temp.value,
    }
    response = request("POST", secrets.api_endpoint + "services/light/" + ("turn_on" if state.state else "turn_off"), headers={
        "Authorization": "Bearer " + secrets.api_token,
    }, json=data)
    print("Update response code: " + str(response.status_code))