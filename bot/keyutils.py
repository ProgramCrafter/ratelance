from utils import KEY_GENERATOR_SALT
from base64 import b16encode
import nacl.signing
import hashlib

class KeyCustodialUtils:
    @staticmethod
    def get_keypair_for_user(chat_id):
        user_secret_uid = (KEY_GENERATOR_SALT + str(chat_id) + KEY_GENERATOR_SALT).encode('utf-8')
        secret_bytes = hashlib.sha256(user_secret_uid).digest()
        
        secret_key_obj = nacl.signing.SigningKey(secret_bytes)
        public_bytes = secret_key_obj.verify_key.encode()
        
        public_key_armored = 'pub:ed25519:vk:' + b16encode(public_bytes).decode('ascii')
        secret_key_armored = 'prv:ed25519:sk:' + b16encode(secret_bytes).decode('ascii')
        key_id = hashlib.sha256(public_key_armored.encode('ascii')).hexdigest()[::8]
        
        return {
            'public': public_bytes,
            'secret': secret_bytes,
            'key_id': key_id,
            'public_armored': public_key_armored,
            'secret_armored': secret_key_armored
        }
