# version=1.0.1
from microwifimanager.manager import WifiManager
from adc_sub import ADC_substitute
import umail
import urequests as requests
import ujson
from machine import Pin, PWM, deepsleep
import uos
import gc
from time import sleep

wlan = WifiManager().get_connection()

if wlan is None:
    print("Could not initialize the network connection.")
    while True:
        pass  # you shall not pass :D 

###################Pins########################################
#config_btn = Pin(14, Pin.IN, Pin.PULL_UP)
#battery_pin = Pin(4, Pin.IN)
adc_pin = Pin(35, Pin.IN)
adc = ADC_substitute(adc_pin)
buzzer_pin = Pin(5, Pin.OUT)
#battery_adc= ADC_substitute(battery_pin)
#alarm_led = Pin(8, Pin.OUT)
#alarm_led.off()
buzzer_pwm = PWM(buzzer_pin, duty=0)
#stop_alarm_btn = Pin(7, Pin.IN)

###########Variables###############################
with open("config.json", "r") as file:
    data = ujson.load(file)
    whatsapi = data["whatsapi"]
    email = data["email"]
    whatsapp = data["whatsapp"]
    device_id = data["device_id"]


#smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)


whatsapp_batmsg10 = f'WARNING%21%20LeakLytics%20device%20%7B{device_id}%7D%20is%20running%20low%20on%20battery%2C%20please%20change%20the%20battery%20as%20soon%20as%20possible%21' #YOUR MESSAGE HERE (URL ENCODED)https://www.urlencoder.io/

whatsapp_batmsg5 = f'WARNING%2521%2520LeakLytics%2520device%2520%257B{device_id}%257D%2520is%2520running%2520low%2520on%2520battery%252C%2520please%2520change%2520the%2520battery%2520as%2520soon%2520as%2520possible%2521'

alarm_msg = f'ATTENTION%20-%20LEAK%20DETECTED%20FROM%20%7Bdevice_id%7D.%20Please%20check%20the%20area%20immediately%20to%20prevent%20potential%20water%20damage.%20Notifications%20will%20keep%20coming%20until%20%22%22stop%20alarm%22%22%20button%20has%20been%20pressed.'
#Juster udfra endelige microcontroller, er forskellig fra esp til ESP - det her er udfra ESP32 C3 SUPER MINI
a = ((100 - 0) / (4095 - 2414))
b = 0 - (a * 2414)

#----------------------------------Functions------------------------------------------------
def send_message(phone_number, api_key, message):
  #set your host URL
  url = 'https://api.callmebot.com/whatsapp.php?phone='+phone_number+'&text='+message+'&apikey='+api_key

  #make the request
  response = requests.get(url)
  #check if it was successful
  if response.status_code == 200:
    print('Success!')
  else:
    print('Error')
    print(response.text)

def leak_alarm():
    while True:
        smtp.write("Subject: Water Leak Detected – Immediate Attention Required\n\n")
        smtp.send(f"ATTENTION - LEAK DETECTED FROM {device_id}. Please check the area immediately to prevent potential water damage. Notifications will keep coming until ""stop alarm"" button has been pressed. ")
        send_message(whatsapp, alarm_msg, whatsapi)
        machine.lightsleep(600)
        alarm_led.on
        if stop_alarm_btn.value() == 0:
            smtp.send(f"Good news! The leak reported by {device_id} has been cleared. Everything's back to normal.")
            alarm_led.off
            machine.reset()
#-----------------------Updating-----------------------------------
def get_version_from_script(script):
    """Extract version number from the script."""
    for line in script.splitlines():
        if line.startswith("# version="):
            return line.replace("# version=", "").strip()
    return None

def check_for_update():
    url = "https://raw.githubusercontent.com/skrimby1/LeakLytics/refs/heads/main/main.py"  # Your raw GitHub URL
    print("Checking for update from:", url)

    # Send GET request to fetch the file content
    response = requests.get(url)
    if response.status_code == 200:
        new_script = response.text
        print(new_script)
        new_version = get_version_from_script(new_script)

        if new_version != CURRENT_VERSION:
            print(f"Update found! Current version: {CURRENT_VERSION}, New version: {new_version}")
            update_script(new_script)  # Update the script if the versions differ
        else:
            print("No update found. Versions are the same.")
        response.close()
    else:
        print("Failed to check for updates:", response.status_code)

def update_script(new_script):
    # Save the new script to a temporary file
    with open("new_main.py", "w") as f:
        f.write(new_script)
    print("New script saved as new_main.py.")

    # Replace the old main.py with the new one
    uos.rename("new_main.py", "main.py")
    print("Update successful! Restarting...")

    uos.sync()  # Make sure everything is written to disk
    machine.reset()  # Restart the ESP32 to apply the updated main.py

check_for_update()
#----------------------------Sounds----------------------------------------------------------------


def buzzer(pwm_object, frequency, tone_duration, silence_duration):
    pwm_object.duty(20)
    pwm_object.freq(frequency)
    sleep(tone_duration)
    pwm_object.duty(0)
    sleep(silence_duration)

def opening_snd():
    buzzer(buzzer_pwm, 659, 0.15, 0.05)
    buzzer(buzzer_pwm, 659, 0.15, 0.05)  
    buzzer(buzzer_pwm, 659, 0.15, 0.05)  
    buzzer(buzzer_pwm, 523, 0.15, 0.05)  
    buzzer(buzzer_pwm, 392, 0.30, 0)      

#---------------------------------Main-------------------------------------------------------------
opening_snd()
#Battery notification proccess
while True:
    reading_adc = adc.read_adc()
    #reading_battery = battery_adc.read_adc()
    batteriprocent = a * reading_battery + b
    batteriprocent
    if batteryprocent < 10:
        smtp.send(f"WARNING! LeakLytics device {device_id} has 10% charge left, please change the battery as soon as possible!")
        send_message(whatsapp, whatsapi, whatsapp_batmsg10)
    if batteryprocent < 5:
        smtp.send(f"WARNING! LeakLytics device {device_id} is at a CRITICAL 5% battery level, battery needs to be changed now or else leaks won't be detected soon!") 
        send_message(whatsapp, whatsapi, whatsapp_batmsg5)
    if reading_adc == 4095:
        leak_email()
    #machine.deepsleep(900)
machine.reset()
