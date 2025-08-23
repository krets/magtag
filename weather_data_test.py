import json

import requests

params = {"lat": 52.5200, "lon": 13.4050}
headers = {"User-Agent": "Magtag 0.1.2/ (jesse@krets.com)"}
response = requests.get("https://api.met.no/weatherapi/locationforecast/2.0/compact", params=params, headers=headers)
data = response.json()
# print(response.text)
print(json.dumps(data, indent=4))