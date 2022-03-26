from machine import Pin, ADC, Timer
from ujson import dumps
import time

from models import LightState, AnalogueValue
from hass import fetch_state, update_state

pin_pot_sw = Pin(4, Pin.IN, Pin.PULL_UP)
pin_pot_dt = Pin(5, Pin.IN)
pin_pot_clk = Pin(16, Pin.IN)
pin_pot_brightness = ADC(Pin(35))
pin_pot_brightness.atten(ADC.ATTN_11DB)
pin_pot_brightness.width(ADC.WIDTH_9BIT)
pin_pot_color_temp = ADC(Pin(34))
pin_pot_color_temp.atten(ADC.ATTN_11DB)
pin_pot_color_temp.width(ADC.WIDTH_9BIT)
pin_switch = Pin(27, Pin.IN)

last_clk = 0
last_pot_sw = 1

step = 10

def convert_255(value):
    return min(round(value * 255 / 500), 255)

def convert_mired(value):
    range_min = 153
    range_max = 285
    range = range_max - range_min
    return range - min(round(value * range / 500), range) + range_min

def step_changed(new_value, old_value):
    return abs(new_value - old_value) > step

def ema(value, ema_s, ema_a):
    return (ema_a * value) + ((1 - ema_a) * ema_s)

def apply_value(analogue_value, value, ema_a):
    analogue_value.ema_s = ema(value, analogue_value.ema_s, ema_a)
    if (step_changed(analogue_value.ema_s, analogue_value.value)):
        analogue_value.value = round(analogue_value.ema_s)
        return True
    return False
    
import wifi
wifi.do_connect()

light_state = fetch_state()
if light_state == None:
    light_state = LightState(False, 255, 300)

ema_a = 0.4

last_switch_state = False

updateTimer = Timer(-1)

while True:
    changed = False

    brightness_reading = convert_255(pin_pot_brightness.read())
    if apply_value(light_state.brightness, brightness_reading, ema_a):
        changed = True
        print("brightness: " + str(light_state.brightness.value))

    color_temp_reading = convert_mired(pin_pot_color_temp.read())
    if apply_value(light_state.color_temp, color_temp_reading, ema_a):
        changed = True
        print("color temp: " + str(light_state.color_temp.value))
        
    switch_pressed = pin_switch.value() == 1
    if (switch_pressed and switch_pressed != last_switch_state):
        changed = True
        light_state.state = not light_state.state
        print('light on: ' + str(light_state.state))
    last_switch_state = switch_pressed

    if changed:
        updateTimer.deinit()
        updateTimer.init(
            mode=Timer.ONE_SHOT,
            period=500,
            callback=lambda t:update_state(light_state)
        )
        

    time.sleep_us(10)
