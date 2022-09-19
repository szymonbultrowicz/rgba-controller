import math
from machine import Pin, ADC, Timer, I2C, deepsleep
import time
import ssd1306
import esp32
import config

from models import LightState, AnalogueValue
from hass import fetch_state, turn_on, update_state

screen_width = 128
screen_height = 64
char_width = 8
char_height = 8

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

if(config.display_available):
    display = ssd1306.SSD1306_I2C(screen_width, screen_height, I2C(0))
    display.poweron()
else:
    display = None

last_clk = 0
last_pot_sw = 1

step = 10

toast_timer = Timer(3)

mired_range_min = 153
mired_range_max = 285
mired_range = mired_range_max - mired_range_min

def convert_255(value):
    return min(round(value * 255 / 500), 255)

def convert_to_mired(value):
    return mired_range - min(round(value * mired_range / 500), mired_range) + mired_range_min

def convert_mired_to_kelvin(value):
    range_mired = mired_range_max - mired_range_min
    range_kelvin_min = 3500
    range_kelvin_max = 6500
    range_kelvin = range_kelvin_max - range_kelvin_min
    return round((1 - (value - mired_range_min) / range_mired) * range_kelvin + range_kelvin_min)

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

def toast_print(text, autoclear=False):
    if(not config.display_available):
        return
    display.fill_rect(0, 0, screen_width, char_height, 0)
    x = math.floor((screen_width / char_width - len(text)) / 2) * char_width
    display.text(text, x, 0)
    display.show()
    if autoclear:
        toast_timer.deinit()
        toast_timer.init(
            mode=Timer.ONE_SHOT,
            period=2000,
            callback=lambda t:toast_clear()
        )

def toast_clear():
    if(not config.display_available):
        return
    toast_timer.deinit()
    display.fill_rect(0, 0, screen_width, char_height, 0)
    display.show()

def update_display_text(display, light_state):
    # text
    v_offset = 28
    display.fill_rect(0, v_offset, screen_width, char_height, 0)
    display.text(str(round(light_state.brightness.value * 100 / 255)) + '%', 0, v_offset)
    display.text(str(convert_mired_to_kelvin(light_state.color_temp.value)) + 'K', screen_width - (5 * char_width), v_offset)

def update_display_temp_bar(display, light_state):
    v_offset = 40
    bar_height = 10
    display.fill_rect(0, v_offset, screen_width, bar_height, 0)
    display.text("W", 0, v_offset + 1)
    display.text("C", screen_width - 1 - char_width, v_offset + 1)
    bar_width = screen_width - 2*(char_width + 2)
    display.fill_rect(char_width + 2, v_offset + 2, bar_width, bar_height - 4, 0b1)
    temp_position = round((mired_range_max - light_state.color_temp.value) / mired_range * (bar_width - 4))
    display.fill_rect(char_width + 2 + temp_position, v_offset, 5, bar_height, 0b1)
    display.fill_rect(char_width + 3 + temp_position, v_offset + 2, 3, bar_height - 4, 0)

def update_display_brightness_bar(display, light_state):
    bar_height = 10
    v_offset = screen_height - 1 - bar_height
    display.fill_rect(0, v_offset, screen_width, bar_height, 0)
    brightness_width = math.ceil(light_state.brightness.value / 255 * screen_width)
    display.fill_rect(0, v_offset, brightness_width, bar_height, 0b1)

def update_display(display, light_state):
    if(not config.display_available):
        return
    update_display_text(display, light_state)
    update_display_temp_bar(display, light_state)
    update_display_brightness_bar(display, light_state)

    display.show()

def turn_off(display):
    print('Going to sleep')
    display.poweroff()
    deepsleep()
    # deepsleep()

def refresh_sleep_timer(timer, display):
    print('Prolonging awake')
    timer.deinit()
    timer.init(
        mode=Timer.ONE_SHOT,
        period=10*1000,
        callback=lambda t:turn_off(display)
    )


display.fill(0)
toast_print("Connecting")

import wifi
wifi.do_connect()

turn_on(toast_print)

toast_print("Fetching state")

light_state = fetch_state()
if light_state == None:
    light_state = LightState(False, 255, 300)
update_display(display, light_state)
toast_clear()

ema_a = 0.4

last_switch_state = False

update_timer = Timer(1)
sleep_timer = Timer(2)
refresh_sleep_timer(sleep_timer, display)

esp32.wake_on_ext0(pin = pin_switch, level = esp32.WAKEUP_ANY_HIGH)

while True:
    changed = False
    delay_enabled = True
    fetch = False

    brightness_reading = convert_255(pin_pot_brightness.read())
    if apply_value(light_state.brightness, brightness_reading, ema_a):
        changed = True
        print("brightness: " + str(light_state.brightness.value))

    color_temp_reading = convert_to_mired(pin_pot_color_temp.read())
    if apply_value(light_state.color_temp, color_temp_reading, ema_a):
        changed = True
        print("color temp: " + str(light_state.color_temp.value))
        
    switch_pressed = pin_switch.value() == 1
    if (switch_pressed and switch_pressed != last_switch_state):
        light_state.state = not light_state.state
        changed = True
        print('light on: ' + str(light_state.state))
        delay_enabled = False
    last_switch_state = switch_pressed
    

    if changed:
        refresh_sleep_timer(sleep_timer, display)
        update_timer.deinit()
        update_display(display, light_state)
        if delay_enabled:
            update_timer.init(
                mode=Timer.ONE_SHOT,
                period=500,
                callback=lambda t:update_state(light_state, toast_print)
            )
        else:
            update_state(light_state, toast_print)

    if fetch:
        toast_print("Fetching state")
        light_state = fetch_state()
        update_display(display, light_state)
        

    time.sleep_us(20)
