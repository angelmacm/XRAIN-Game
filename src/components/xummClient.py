from components.config import xummConfig

from xumm import XummSdk

class XummClient:
    def __init__(self):
        self.xummSdk = XummSdk(xummConfig['API_KEY'], xummConfig['API_SECRET'])
        
    def createSignIn(self):
        signInInfo = self.xummSdk.payload.create(payload={
            'TransactionType': "SignIn"
            })
         
        return signInInfo
    
    def checkStatus(self, uuid):
        status = self.xummSdk.payload.get(uuid)
        return status.response.to_dict()
    
    def createXrainPaymentRequest(self, recipient: str, amount: float, coinHex:str = "XRP"):
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
            
        paymentRequest = self.xummSdk.payload.create(payload={
            'txjson': txJson,
            'options':{
                "force_network": "TESTNET",
                "expire": 30,
                'submit': True
            },
            "custom_meta": {
            "identifier": f"{coinHex} Payment",
            "instruction": f"Scan to pay {amount} {coinHex}"
        }
        })
        return paymentRequest