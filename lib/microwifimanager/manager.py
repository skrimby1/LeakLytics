import network
import socket
import ure
import time
import errno
from microwifimanager.microDNSSrv import MicroDNSSrv
import json

NETWORK_PROFILES = 'wifi.dat'

wlan_ap = network.WLAN(network.AP_IF)
wlan_sta = network.WLAN(network.STA_IF)

class WifiManager:

    # authmodes: 0=open, 1=WEP, 2=WPA-PSK, 3=WPA2-PSK, 4=WPA/WPA2-PSK
    def __init__(self, ssid='LeakLytics-Portal', password='dunses1234', authmode=4):
        self.ssid = ssid
        self.password = password
        self.authmode = authmode
        self.server_socket = None

    def get_connection(self):
        """return a working WLAN(STA_IF) instance or None"""

        # First check if there already is any connection:
        if wlan_sta.isconnected():
            return wlan_sta

        connected = False
        try:
            # ESP connecting to WiFi takes time, wait a bit and try again:
            time.sleep(3)
            if wlan_sta.isconnected():
                return wlan_sta

            # Read known network profiles from file
            profiles = read_profiles()

            # Search WiFis in range
            wlan_sta.active(True)
            networks = wlan_sta.scan()

            AUTHMODE = {0: "open", 1: "WEP", 2: "WPA-PSK", 3: "WPA2-PSK", 4: "WPA/WPA2-PSK"}
            for ssid, bssid, channel, rssi, authmode, hidden in sorted(networks, key=lambda x: x[3], reverse=True):
                ssid = ssid.decode('utf-8')
                encrypted = authmode > 0
                print("ssid: %s chan: %d rssi: %d authmode: %s" % (ssid, channel, rssi, AUTHMODE.get(authmode, '?')))
                if encrypted:
                    if ssid in profiles:
                        password = profiles[ssid]
                        connected = do_connect(ssid, password)
                    else:
                        print("skipping unknown encrypted network")
                else:  # open
                    connected = do_connect(ssid, None)
                if connected:
                    break

        except OSError as e:
            print("exception", str(e))

        # start web server for connection manager:
        if not connected:
            connected = self.start()

        return wlan_sta if connected else None


    def stop(self):
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

    
    def start(self, port=80):

        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]

        self.stop()

        wlan_sta.active(True)
        wlan_ap.active(True)

        wlan_ap.config(essid=self.ssid, password=self.password, authmode=self.authmode)

        self.server_socket = socket.socket()
        self.server_socket.bind(addr)
        self.server_socket.listen(1)

        mdns = MicroDNSSrv.Create({ '*' : '192.168.4.1' })

        print('Connect to WiFi ssid ' + self.ssid + ', default password: ' + self.password)
        print('and open browser window (captive portal should redirect)')
        print('Listening on:', addr)

        while True:
            if wlan_sta.isconnected():
                # Allow confirmation page to display before shutting down network
                time.sleep(3)
                mdns.Stop()
                self.stop()
                wlan_ap.active(False)
                return True

            client, addr = self.server_socket.accept()
            print('client connected from', addr)
            try:
                client.settimeout(5.0)

                request = b""
                try:
                    while "\r\n\r\n" not in request:
                        request += client.recv(512)
                except OSError:
                    pass

                # Handle form data from Safari on macOS and iOS; it sends \r\n\r\nssid=<ssid>&password=<password>
                try:
                    request += client.recv(1024)
                    print("Received form data after \\r\\n\\r\\n(i.e. from Safari on macOS or iOS)")
                except OSError:
                    pass

                print("Request is: {}".format(request))
                if "HTTP" not in request:  # skip invalid requests
                    continue

                # version 1.9 compatibility
                try:
                    url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
                except Exception:
                    url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")
                print("URL is {}".format(url))


                # TODO getting "generate_204 as address"
                if url == "configure":
                    handle_configure(client, request)
                else:
                    handle_root(client)

            finally:
                client.close()


def read_profiles():
    with open(NETWORK_PROFILES) as f:
        lines = f.readlines()
    profiles = {}
    for line in lines:
        ssid, password = line.strip("\n").split(";")
        profiles[ssid] = password
    return profiles


def write_profiles(profiles):
    lines = []
    for ssid, password in profiles.items():
        lines.append("%s;%s\n" % (ssid, password))
    with open(NETWORK_PROFILES, "w") as f:
        f.write(''.join(lines))


def do_connect(ssid, password):
    wlan_sta.active(True)
    if wlan_sta.isconnected():
        return None
    print('Trying to connect to %s...' % ssid)
    wlan_sta.connect(ssid, password)
    for retry in range(200):
        connected = wlan_sta.isconnected()
        if connected:
            break
        time.sleep(0.1)
        print('.', end='')
    if connected:
        print('\nConnected. Network config: ', wlan_sta.ifconfig())
    else:
        print('\nFailed. Not Connected to: ' + ssid)
    return connected


def send_header(client, status_code=200, content_length=None ):
    client.sendall("HTTP/1.0 {} OK\r\n".format(status_code))
    client.sendall("Content-Type: text/html\r\n")
    if content_length is not None:
        client.sendall("Content-Length: {}\r\n".format(content_length))
    client.sendall("\r\n")


def send_response(client, payload, status_code=200):
    content_length = len(payload)
    send_header(client, status_code, content_length)
    if content_length > 0:
        client.sendall(payload)
    client.close()


def handle_root(client):
    try:
        wlan_sta.active(True)
        ssids = sorted(ssid.decode('utf-8') for ssid, *_ in wlan_sta.scan())
        send_header(client)
        client.sendall("""\
        <html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeakLytics Portal</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            text-align: center;
            margin: 0;
            padding: 20px;
        }
        .container {
            background: white;
            max-width: 600px;
            margin: auto;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #333;
        }
        .form-group {
            margin: 15px 0;
            text-align: left;
        }
        label {
            font-weight: bold;
        }
        #networks {
            margin-bottom: 50px;
        }
        input[type="password"], input[type="submit"] {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            
        }
        input[type="tel"], input[type="submit"] {
            width: 60%;
            padding: 10px;
            margin-top: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        input[type="number"], input[type="submit"] {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        input[type="email"], input[type="submit"] {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        
        input[type="text"], input[type="submit"] {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        
        }
        
        input[type="submit"] {
            background-color: #377dda;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        input[type="submit"]:hover {
            background-color: #4d91e4;
        }
        .add-email-btn {
            background-color: #28a745;
            color: white;
            border: none;
            width: 20%;
            padding: 10px;
             -radius: 5px;
            cursor: pointer;
            margin-top: 5px;
        }
        .add-email-btn:hover {
            background-color: #218838;
        }
        .warning {
            color: red;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .info {
            margin-top: 20px;
            font-size: 0.9em;
        }
        .info a {
            color: #2b3ea6;
            text-decoration: none;
        }
    </style>
    <script>
    function addEmailField() {
        let container = document.getElementById("email-container");

        // Create a wrapper div for email input and delete button
        let div = document.createElement("div");
        div.style.display = "flex";
        div.style.alignItems = "center";
        div.style.marginTop = "5px";

        // Create the email input field
        let input = document.createElement("input");
        input.type = "email";
        input.name = "email";
        input.required = true;
        input.placeholder = "Enter another email";
        input.style.flex = "1"; // Makes the input take most of the space

        // Create the delete button (X)
        let deleteBtn = document.createElement("button");
        deleteBtn.innerHTML = "✖";
        deleteBtn.style.marginLeft = "10px";
        deleteBtn.style.marginTop = "15px";
        deleteBtn.style.background = "transparent"; // Make background transparent
        deleteBtn.style.color = "white"; // Ensure the text color is white
        deleteBtn.style.border = "none";
        deleteBtn.style.padding = "5px 10px";
        deleteBtn.style.borderRadius = "5px";
        deleteBtn.style.cursor = "pointer";
        deleteBtn.style.fontSize = "16px"; // Adjust font size if necessary

        // Add hover and focus styles
        deleteBtn.style.transition = "background-color 0.3s ease"; // Smooth transition
        deleteBtn.onmouseover = function () {
            deleteBtn.style.backgroundColor = "rgba(255, 255, 255, 0.2)"; // Slight white background on hover
        };
        deleteBtn.onmouseout = function () {
            deleteBtn.style.backgroundColor = "transparent"; // Remove background when not hovering
        };
        deleteBtn.onfocus = function () {
            deleteBtn.style.outline = "none"; // Remove outline for focus
        };

        // Remove the email input when the delete button is clicked
        deleteBtn.onclick = function () {
            container.removeChild(div);
        };

        // Append input and delete button to the wrapper div
        div.appendChild(input);
        div.appendChild(deleteBtn);

        // Append the wrapper div to the email container
        container.appendChild(div);
    }
    </script>
    </head>
    <body>
            <div class="container">
                <h1>LeakLytics Configuration Portal</h1>
                <form action="configure" method="post">
                    <div class="form-group">
                        <label for="device_id">Device Name:</label>
                        <input id="device_id" name="device_id" type="text" required placeholder="Example: Leaksensor-1" />
                    </div>
                    <div class="form-group" id="email-container">
                        <label for="email">E-mail for notifications:</label>
                        <input id="email" name="email" type="email" required placeholder="Enter at least one email" />
                    </div>
                    <button type="button" class="add-email-btn" onclick="addEmailField()">Add Email</button>
                    <div class="form-group">
                        <label for="whatsapp">WhatsApp number (Optional):</label>
                        <div style="display: flex;">
                            <select id="country-code" name="country_code" style="width: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-right: 10px; margin-top: 10px;">
                                <option value="+1">+1</option>
                                <option value="+52">+52</option>
                                <option value="+45">+45</option>
                            </select>
                            <input id="whatsapp" name="whatsapp" type="tel" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="whatsapi">WhatsApp Bot API-Key (Required for WhatsApp):</label>
                        <input id="whatsapi" name="whatsapi" type="number" placeholder="Typically 6 digits, Example: 888723" />
                    </div>
                    <div class="form-group">
                        <label id="networks">Available Networks:</label><br>
    """)
        while len(ssids):
            ssid = ssids.pop(0)
            client.sendall("""\
                         <input type="radio" name="ssid" value="{0}" required style="margin-top: 10px;"/> {0} <br>
        """.format(ssid))
        client.sendall("""\
                    </div>
                    <div class="form-group">
                        <label for="password">WiFi Password:</label>
                        <input id="password" name="password" type="password" required />
                    </div>
                    <input type="submit" value="Connect" />
                </form>
                <p class="warning">It's highly recommended to perform a test of your LinkLytics device after configuration is done</p>
                <div class="info">
                    <h3>Guides:</h3>
                    <ul>
                        <li><a href="https://github.com/cpopp/MicroPythonSamples" target="_blank" rel="noopener">How to configure your LeakLytics device</a></li>
                        <li><a href="https://github.com/tayfunulu/WiFiManager" target="_blank" rel="noopener">How to configure WhatsApp for notifications</a></li>
                    </ul>
                </div>
            </div>
        </body>
        </html>

    """)
        client.close()
    except Exception as e:
        if e.errno == errno.ECONNRESET:
            pass
        else:
            raise

def handle_configure(client, request):
    match = ure.search("ssid=([^&]*)&password=(.*)", request)
    print("Raw request:", request)  # Debugging: Check incoming request format

    # Extract the POST data (after \r\n\r\n in HTTP headers)
    body_start = request.find(b"\r\n\r\n")
    if body_start == -1:
        send_response(client, "Invalid request format", status_code=400)
        return False

    form_data = request[body_start + 4:]  # Extract the body part

    # Debugging: Print form data to see if it's captured correctly
    print("Extracted form data:", form_data)

    # Initialize dictionary to store form parameters
    params = {}  # ✅ FIX: Define params before using it

    # Parse form data manually into a dictionary
    form_data = form_data.decode("utf-8")
    for pair in form_data.split("&"):
        key_value = pair.split("=")
        if len(key_value) == 2:
            key, value = key_value
            key = key.strip()
            value = value.strip().replace("%3F", "?").replace("%21", "!").replace("+", " ").replace("%26", "&")

            # Handle multiple email fields (store them in a list)
            if key == "email":
                if key in params:
                    params[key].append(value)
                else:
                    params[key] = [value]
            else:
                params[key] = value  # ✅ FIX: Ensure all key-value pairs are stored

    # Debugging: Print parsed parameters
    print("Parsed parameters:", params)

    # Check if required fields are present
    required_fields = ["ssid", "password", "device_id", "email"]
    for field in required_fields:
        if field not in params or not params[field]:
            send_response(client, f"Missing required parameter: {field}", status_code=400)
            return False

    ssid = params["ssid"]
    password = params["password"]
    device_id = params["device_id"]
    email_list = params["email"] if isinstance(params["email"], list) else [params["email"]]
    whatsapp = params.get("whatsapp", "")
    whatsapi = params.get("whatsapi", "")

    # Store device-specific configurations
    config_data = {
        "device_id": device_id,
        "email": email_list,  # Store multiple emails as a list
        "whatsapp": whatsapp,
        "whatsapi": whatsapi
    }

    with open("config.json", "w") as f:
        json.dump(config_data, f)

    if do_connect(ssid, password):
        response = """
        <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkLytics Device Connected!</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            display: inline-block;
        }
        h1 {
            color: #333;
        }
        .status {
            color: #28a745;
            font-size: 1.2em;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>LeakLytics Device Successfully Connected!</h1>
        <p class="status">Connected to WiFi network: <strong>%(ssid)s</strong></p>
    </div>
</body>
</html>
        """ % dict(ssid=ssid)
        send_response(client, response)
        try:
            profiles = read_profiles()
        except OSError:
            profiles = {}
        profiles[ssid] = password
        write_profiles(profiles)

        time.sleep(1)
        return True
    else:
        send_response(client, "Connection failed. Check WiFi details.", status_code=400)
        return False
