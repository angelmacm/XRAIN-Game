from components.config import xummConfig

from xumm import XummSdk
from xumm.resource.payload import XummGetPayloadResponse, XummPostPayloadResponse

class XummClient:
    def __init__(self):
        self.xummSdk = XummSdk(xummConfig['API_KEY'], xummConfig['API_SECRET'])
        
    def createSignIn(self) -> XummPostPayloadResponse:
        signInInfo = self.xummSdk.payload.create(payload={
            'TransactionType': "SignIn"
            })
         
        return signInInfo
    
    def checkStatus(self, uuid) -> XummGetPayloadResponse:
        status = self.xummSdk.payload.get(uuid)
        return status.response
    
    def createXrainPaymentRequest(self, recipient: str, amount: float, coinHex:str = "XRP") -> XummPostPayloadResponse:
        txJson = {
            "TransactionType": "Payment",
            "Destination": recipient,
        }
        
        if coinHex.upper() == "XRP":
            txJson['Amount'] = str(amount * 1000000)
        else:
            txJson['Amount'] = {
                "currency": coinHex,
                "value": str(amount),
                "issuer": 'rh3tLHbXwZsp7eciw2Qp8g7bN9RnyGa2pF'
            }
            
        coinHexText = 'XRAIN' if coinHex.upper() != 'XRP' else 'XRP' 
        
        paymentRequest = self.xummSdk.payload.create(payload={
            'txjson': txJson,
            'options':{
                "force_network": "MAINNET",
                "expire": 30,
                'submit': True
            },
            "custom_meta": {
            "instruction": f"Scan to pay {amount} {coinHexText}"
        }
        })
        return paymentRequest