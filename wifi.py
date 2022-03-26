import secrets

def do_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(secrets.wifi_ssid, secrets.wifi_password)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())