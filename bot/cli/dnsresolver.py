from tonsdk.utils import Address
import requests


class TONDNSResolutionError(Exception): pass

def resolve_to_userfriendly(addr):
    try:
        return Address(addr).to_string(True, True, True)
    except:
        # resolving TON DNS
        if not set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_.').issuperset(addr):
            raise TONDNSResolutionError('Invalid characters')
        if len(addr) < 3 or len(addr) > 127:
            raise TONDNSResolutionError('Invalid length')
        if not addr.endswith('.ton') and not addr.endswith('.t.me'):
            raise TONDNSResolutionError('Unsupported top-level domain')
        
        resolved = requests.get(f'https://tonapi.io/v2/dns/{addr}/resolve').json()
        if 'wallet' not in resolved:
            raise TONDNSResolutionError('Domain not pointing at wallet')
        
        return Address(resolved['wallet']['address']).to_string(True, True, True)
