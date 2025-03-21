from machine import Pin, PWM
from time import sleep


buzzer_pin = 3

buzzer_PIN = Pin(buzzer_pin, Pin.OUT)

buzzer_pwm = PWM(buzzer_pin, duty=0)


def buzzer(pwm_object, frequency, tone_duration, silence_duration):
    pwm_object.duty(20)
    pwm_object.freq(frequency)
    sleep(tone_duration)
    pwm_object.duty(0)
    sleep(silence_duration)
    
def opening_snd():
    buzzer(buzzer_pwm, 800, 0.3, 0)
    buzzer(buzzer_pwm, 850, 0.3, 0)
    buzzer(buzzer_pwm, 900, 0.3, 0)
    buzzer(buzzer_pwm, 1000, 0.5, 0)
    buzzer(buzzer_pwm, 1200, 0.2, 0)
opening_snd()

def alarm():
    buzzer(buzzer_pwm, 300, 5, 0)
    
