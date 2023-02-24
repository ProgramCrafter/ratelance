from colors import nh, h, nb, b, ns, s

from base64 import b16decode, b64encode, urlsafe_b64encode
from getpass import getpass

import tonsdk.contract.wallet
import tonsdk.crypto
import tonsdk.utils
import nacl.signing
import tonsdk.boc

# TODO: move `requests` out of functions/modules where secret keys are accessed
import requests



def retrieve_keypair(auth_way: str):
  if auth_way == 'm':
    while True:
      mnemonic = getpass(f'{b}Your wallet mnemonic (not echoed):{nb} ').split()
      if tonsdk.crypto.mnemonic_is_valid(mnemonic): break
      
      use_anyway = input(f'{b}Entered mnemonic is invalid. Use it anyway?{nb} [y/n] ').lower()
      if use_anyway == 'y': break
    
    _, secret_key = tonsdk.crypto.mnemonic_to_wallet_key(mnemonic)
    secret_key = secret_key[:32]
    del mnemonic
  elif auth_way == 's':
    while True:
      secret_hex = getpass(f'{b}Your secret key in HEX (not echoed):{nb} ').upper()
      if not set('0123456789ABCDEF').issuperset(secret_hex):
        print('Invalid characters met')
      elif len(secret_hex) != 64:
        print('Invalid key length')
      else:
        break
    
    secret_key = b16decode(secret_hex)
    del secret_hex
  else:
    raise Exception('unsupported auth way for retrieving keypair')
  
  secret_key_obj = nacl.signing.SigningKey(secret_key)
  public_key = secret_key_obj.verify_key.encode()
  secret_key = secret_key_obj.encode() + public_key  # making secret key 64-byte
  return public_key, secret_key


def retrieve_auth_wallet(auth_way: str, plugin_only=False):
  public_key, secret_key = retrieve_keypair(auth_way)
  
  WALLET_V = ['v4r2'] if plugin_only else ['v3r1', 'v3r2', 'v4r2']
  WALLET_PROMPT = 'Enter wallet version (' + b + '/'.join(WALLET_V) + nb + '): '
  while (wallet_ver := input(WALLET_PROMPT).lower()) not in WALLET_V: pass
  
  wallet_class = tonsdk.contract.wallet.Wallets.ALL[wallet_ver]
  return wallet_class(public_key=public_key, private_key=secret_key)


def sign_for_sending(message: tonsdk.boc.Cell,
                     dest: tonsdk.utils.Address,
                     state_init: tonsdk.boc.Cell,
                     value_nton: int,
                     description: str) -> tonsdk.boc.Cell:
  print(f'{h}Attempting to send{nh}', repr(description))
  print(f'{h}Destination:{nh}', dest.to_string(True, True, True))
  print(f'{h}TON amount: {nh}', value_nton / 1e9)
  print(f'{h}Message BOC:{nh}', b64encode(message.to_boc(False)).decode('ascii'))
  print()
  
  WAY_PROMPT = f'Send via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]/ton link [{h}t{nh}]? '
  while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's', 't'): pass
  
  if auth_way == 't':
    addr = dest.to_string(True, True, True)
    boc  = urlsafe_b64encode(message.to_boc(False)).decode('ascii')
    link = f'ton://transfer/{addr}?bin={boc}&amount={value_nton}'
    if state_init:
      link += '&init='
      link += urlsafe_b64encode(state_init.to_boc(False)).decode('ascii')
    
    print(f'\nTransfer link: {b}{link}{nb}')
    
    return None
  
  wallet = retrieve_auth_wallet(auth_way)
  addr = wallet.address.to_string(True, True, True)
  
  print('Ready to do transfer from', addr)
  
  while (confirm := input(f'{h}Confirm? [y/n] {nh}').lower()) not in ('y', 'n'):
    pass
  
  if confirm == 'n': return None
  
  link = f'https://tonapi.io/v1/wallet/getSeqno?account={addr}'
  seqno = requests.get(link).json().get('seqno', 0)
  
  return wallet.create_transfer_message(dest, value_nton, seqno,
    payload=message, state_init=state_init)['message']


def sign_send(message: tonsdk.boc.Cell,
              dest: tonsdk.utils.Address,
              state_init: tonsdk.boc.Cell,
              value_nton: int,
              description: str):
  signed_msg = sign_for_sending(message, dest, state_init, value_nton, description)
  if signed_msg:
    requests.post('https://tonapi.io/v1/send/boc', json={
      'boc': b64encode(signed_msg.to_boc(False)).decode('ascii')
    })


def sign_plugin(plugin_init: tonsdk.boc.Cell, value_nton: int,
                description: str) -> tonsdk.boc.Cell:
  print(f'{h}Attempting to install plugin{nh}', repr(description))
  print(f'{h}Init BOC:   {nh}', b64encode(plugin_init.to_boc(False)).decode('ascii'))
  print(f'{h}TON amount: {nh}', value_nton / 1e9)
  print(f'{h}Message BOC:{nh}', b64encode(message.to_boc(False)).decode('ascii'))
  print()
  
  WAY_PROMPT = f'Install via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]? '
  while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's'): pass
  
  wallet = retrieve_auth_wallet(auth_way, plugin_only=True)
  addr = wallet.address.to_string(True, True, True)
  
  print('Ready to install plugin to', addr)
  
  while (confirm := input(f'{h}Confirm? [y/n] {nh}').lower()) not in ('y', 'n'):
    pass
  
  if confirm == 'n': return None
  
  link = f'https://tonapi.io/v1/wallet/getSeqno?account={addr}'
  seqno = requests.get(link).json().get('seqno', 0)
  
  msg_body = wallet.create_signing_message(seqno, without_op=True)
  msg_body.store_uint(1, 8)         # deploy + install plugin
  msg_body.store_int(0, 8)          # workchain 0
  msg_body.store_coins(value_nton)  # initial plugin balance
  msg_body.store_ref(plugin_init)   
  msg_body.store_ref(tonsdk.boc.Cell())
  
  return wallet.create_external_message(msg_body, seqno)['message']


def sign_install_plugin(plugin_init: tonsdk.boc.Cell, value_nton: int,
                        description: str) -> tonsdk.boc.Cell:
  signed_msg = sign_plugin(plugin_init, value_nton, description)
  if signed_msg:
    requests.post('https://tonapi.io/v1/send/boc', json={
      'boc': b64encode(signed_msg.to_boc(False)).decode('ascii')
    })



