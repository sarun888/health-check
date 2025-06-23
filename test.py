import requests
import ssl
from urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount("https://", TLSAdapter())

url = "https://ml-health-check-staging.westeurope.inference.ml.azure.com/score"
headers = {
    "Authorization": "Bearer ",
    "Content-Type": "application/json"
}
payload = {"input_data": "test"}

response = session.post(url, headers=headers, json=payload)
print(response.status_code, response.text)
