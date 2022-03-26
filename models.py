class AnalogueValue:
    def __init__(self, value, ema_s):
        self.value = value
        self.ema_s = ema_s

class LightState:
    def __init__(self, state, brightness, color_temp) -> None:
        self.state = state
        self.brightness = AnalogueValue(brightness, brightness)
        self.color_temp = AnalogueValue(color_temp, color_temp)
