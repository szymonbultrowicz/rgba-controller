from urequests import request
from models import LightState
import secrets
import config


def fetch_state():
    response = request("GET", secrets.api_endpoint + "states/" + config.entity_id, headers={
        "Authorization": "Bearer " + secrets.api_token,
    })

    if (response.status_code > 200):
        print("Failed to fetch recent state, error code: " + str(response.status_code))
        response.close()
        return None
    response_state = response.json()
    response.close()
    light_state = LightState(
        state=response_state["state"] == 'on',
        brightness = response_state["attributes"]["brightness"] if "brightness" in response_state["attributes"] else 100,
        color_temp = response_state["attributes"]["color_temp"] if "color_temp" in response_state["attributes"] else 300,
    )
    return light_state

def turn_on(toast_print):
    toast_print("Turning on")
    data = {"entity_id": config.entity_id}
    response = request("POST", secrets.api_endpoint + "services/light/turn_on", headers={
        "Authorization": "Bearer " + secrets.api_token,
    }, json=data)
    response.close()

def update_state(state, toast_print, busy_pin = None):
    toast_print("Applying")
    data = {"entity_id": config.entity_id} if not state.state else {
        "entity_id": config.entity_id,
        "brightness": state.brightness.value,
        "color_temp": state.color_temp.value,
    }
    if busy_pin is not None:
        busy_pin.on()
    response = request("POST", secrets.api_endpoint + "services/light/" + ("turn_on" if state.state else "turn_off"), headers={
        "Authorization": "Bearer " + secrets.api_token,
    }, json=data)
    print("Update response code: " + str(response.status_code))
    toast_print("Updated (" + str(response.status_code) + ")", True)
    response.close()
    if busy_pin is not None:
        busy_pin.off()