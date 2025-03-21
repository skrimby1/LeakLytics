from machine import Pin
from adc_sub import ADC_substitute
import umail
from time import sleep


pin_adc = 1

whatsapp_batmsg10 = f'WARNING%21%20LeakLytics%20device%20%7B{device_name}%7D%20is%20running%20low%20on%20battery%2C%20please%20change%20the%20battery%20as%20soon%20as%20possible%21' #YOUR MESSAGE HERE (URL ENCODED)https://www.urlencoder.io/

whatsapp_batmsg5 = f'WARNING%2521%2520LeakLytics%2520device%2520%257B{device_name}%257D%2520is%2520running%2520low%2520on%2520battery%252C%2520please%2520change%2520the%2520battery%2520as%2520soon%2520as%2520possible%2521'

#Juster udfra endelige microcontroller, er forskellig fra esp til ESP - det her er udfra ESP32 C3 SUPER MINI
a = ((100 - 0) / (4095 - 2414))
b = 0 - (a * 2414)

device_name = Leakr
while True:
    adc = ADC_substitute(pin_adc)
    reading_adc = adc.read_adc()
    print(reading_adc)
    batteriprocent = a * reading_adc + b
    batteriprocent
    if batteryprocent < 10:
        smtp.send(f"WARNING! LeakLytics device {device_name} is running low on battery, please change the battery as soon as possible!")
        send_message(phone_number, api_key, whatsapp_batmsg10)
    if batteryprocent < 5:
        smtp.send(f"WARNING! LeakLytics device {device_name} is at a CRITICAL battery level, battery needs to be changed now or else leaks won't be detected very soon!") 
        send_message(phone_number, api_key, whatsapp_batmsg5)
