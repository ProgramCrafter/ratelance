from .colors import nh, h, nb, b, ns, s

from base64 import b16decode, b64encode, urlsafe_b64encode
from getpass import getpass
import time

from tonsdk.contract.wallet import Wallets
from tonsdk.contract import Contract
from tonsdk.utils import Address
from tonsdk.boc import Cell
import tonsdk.crypto
import nacl.signing
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
  
  wallet_class = Wallets.ALL[wallet_ver]
  return wallet_class(public_key=public_key, private_key=secret_key)


# orders: list[tuple[to_addr, state_init, payload, amount]]
def sign_multitransfer_body(wallet: Contract, seqno: int,
                            orders: list[tuple[Address,Cell,Cell,int]]) -> Cell:
  assert len(orders) <= 4
  
  send_mode = 3
  signing_message = wallet.create_signing_message(seqno)
  
  for (to_addr, state_init, payload, amount) in orders:
    order_header = Contract.create_internal_message_header(to_addr, amount)
    order = Contract.create_common_msg_info(order_header, state_init, payload)
    signing_message.bits.write_uint8(send_mode)
    signing_message.refs.append(order)
  
  return wallet.create_external_message(signing_message, seqno)['message']


def sign_for_sending(orders: list[tuple[Address,Cell,Cell,int]],
                     description: str, auth_way=None, wallet=None) -> Cell:
  print(f'{h}Sending messages for purpose of{nh}', repr(description))
  
  sum_value = 0
  for (dest, state_init, message, value_nton) in orders:
    init_flag = f'{b}[deploy]{nb}' if state_init else ''
    
    print('===')
    print(f'{h}Destination:{nh}', dest.to_string(True, True, True), init_flag)
    print(f'{h}TON amount: {nh}', value_nton / 1e9)
    print(f'{h}Message BOC:{nh}', b64encode(message.to_boc(False)).decode('ascii'))
    sum_value += value_nton
  
  print('===')
  print(f'{h}Total TON:  {nh} {sum_value / 1e9}')
  print()
  
  if not auth_way:
    WAY_PROMPT = f'Send via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]/ton link [{h}t{nh}]? '
    while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's', 't'): pass
    
  if auth_way == 't':
    print('\nTransfer links:')
    
    for (dest, state_init, message, value_nton) in orders:
      addr = dest.to_string(True, True, True)
      boc  = urlsafe_b64encode(message.to_boc(False)).decode('ascii')
      link = f'ton://transfer/{addr}?bin={boc}&amount={value_nton}'
      if state_init:
        link += '&init='
        link += urlsafe_b64encode(state_init.to_boc(False)).decode('ascii')
      
      print(f'{b}{link}{nb}')
    
    return None
  
  if not wallet:
    wallet = retrieve_auth_wallet(auth_way)
  addr = wallet.address.to_string(True, True, True)
  
  print('Ready to do transfer from', addr)
  
  while (confirm := input(f'{h}Confirm? [y/n] {nh}').lower()) not in ('y', 'n'):
    pass
  
  if confirm == 'n': return None
  
  link = f'https://tonapi.io/v1/wallet/getSeqno?account={addr}'
  seqno = requests.get(link).json().get('seqno', 0)
  
  return sign_multitransfer_body(wallet, seqno, orders)


def sign_send(orders: list[tuple[Address,Cell,Cell,int]],
              description: str, auth_way=None, wallet=None):
  signed_msg = sign_for_sending(orders, description, auth_way, wallet)
  if signed_msg:
    requests.post('https://tonapi.io/v1/send/boc', json={
      'boc': b64encode(signed_msg.to_boc(False)).decode('ascii')
    })


def sign_plugin(plugin_init: Cell, value_nton: int,
                description: str, wallet=None) -> Cell:
  print(f'{h}Attempting to install plugin{nh}', repr(description))
  print(f'{h}Init BOC:   {nh}', b64encode(plugin_init.to_boc(False)).decode('ascii'))
  print(f'{h}TON amount: {nh}', value_nton / 1e9)
  print()
  
  if not wallet:
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
  msg_body.bits.write_uint(1, 8)         # deploy + install plugin
  msg_body.bits.write_int(0, 8)          # workchain 0
  msg_body.bits.write_coins(value_nton)  # initial plugin balance
  msg_body.refs.append(plugin_init)   
  msg_body.refs.append(Cell())
  
  return wallet.create_external_message(msg_body, seqno)['message']


def sign_install_plugin(plugin_init: Cell, value_nton: int,
                        description: str, wallet=None) -> Cell:
  signed_msg = sign_plugin(plugin_init, value_nton, description, wallet)
  if signed_msg:
    requests.post('https://tonapi.io/v1/send/boc', json={
      'boc': b64encode(signed_msg.to_boc(False)).decode('ascii')
    })


def sign_unplug(plugin: str, description: str, wallet=None) -> Cell:
  print(f'{h}Attempting to remove plugin{nh}', repr(description))
  print(f'{h}Address:{nh}', plugin)
  print()
  
  if not wallet:
    WAY_PROMPT = f'Remove via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]? '
    while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's'): pass
    wallet = retrieve_auth_wallet(auth_way, plugin_only=True)
  addr = wallet.address.to_string(True, True, True)
  
  print('Ready to remove plugin from', addr)
  
  while (confirm := input(f'{h}Confirm? [y/n] {nh}').lower()) not in ('y', 'n'):
    pass
  
  if confirm == 'n': return None
  
  link = f'https://tonapi.io/v1/wallet/getSeqno?account={addr}'
  seqno = requests.get(link).json().get('seqno', 0)
  
  plugin_addr = Address(plugin)
  
  msg_body = wallet.create_signing_message(seqno, without_op=True)
  msg_body.bits.write_uint(3, 8)         # remove plugin
  msg_body.bits.write_int(plugin_addr.wc, 8)
  msg_body.bits.write_bytes(plugin_addr.hash_part)
  msg_body.bits.write_coins(5*10**7)     # value to send for destroying
  msg_body.bits.write_uint(int(time.time() * 1000), 64)
  
  return wallet.create_external_message(msg_body, seqno)['message']


def sign_uninstall_plugin(plugin: str, description: str, wallet=None) -> Cell:
  signed_msg = sign_unplug(plugin, description, wallet)
  if signed_msg:
    requests.post('https://tonapi.io/v1/send/boc', json={
      'boc': b64encode(signed_msg.to_boc(False)).decode('ascii')
    })

