from components.config import xummConfig

from xumm import XummSdk

class XummClient:
    def __init__(self):
        self.xummSdk = XummSdk(xummConfig['API_KEY'], xummConfig['API_SECRET'])
        