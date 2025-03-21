
api_key = 'CALLMEBOT_API_KEY'

phone_number = 'YOUR_PHONE_NUMER_INTERNATIONAL_FORMAT'

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

message = 'Hello%20from%20ESP32%20%28micropython%29' #YOUR MESSAGE HERE (URL ENCODED)https://www.urlencoder.io/ 
send_message(phone_number, api_key, message)