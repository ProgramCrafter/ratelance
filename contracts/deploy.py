from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from nacl.bindings import crypto_sign_seed_keypair
from tonsdk.utils import Address, to_nano
from tonsdk.boc import Builder, Cell

import traceback
import requests
import base64
import json
import time


def code_to_init_and_addr(code: bytes) -> tuple[Cell, Address]:
  state_init = Builder()
  state_init.store_uint(6, 5)
  state_init.store_ref(Cell.one_from_boc(code))
  state_init.store_ref(Cell())
  state_init = state_init.end_cell()
  
  si_hash = state_init.bytes_hash()
  addr_hex = '0:' + base64.b16encode(si_hash).decode('ascii')
  
  return state_init, Address(addr_hex)

try:
  with open(__file__ + '/../seed.pk') as f:
    pub_key, prv_key = crypto_sign_seed_keypair(bytes(json.load(f)))
  
  wallet = Wallets.ALL[WalletVersionEnum.v3r1](
    public_key=pub_key, private_key=prv_key, wc=0
  )
  
  seqno = requests.get(
      'https://testnet.tonapi.io/v1/wallet/getSeqno?account='
    + wallet.address.to_string(True, True, True)
  ).json()['seqno']
  
  with open(__file__ + '/../build/boc/contract-job.boc', 'rb') as jc:
    jcs, jca = code_to_init_and_addr(jc.read())
    
    print('Deploying job contract to', jca.to_string(True, True, True))
    
    query = wallet.create_transfer_message(
      jca, to_nano(0.03, 'ton'), seqno, state_init=jcs
    )
    requests.post('https://testnet.tonapi.io/v1/send/boc', json={
      'boc': base64.b64encode(query['message'].to_boc(False)).decode('ascii')
    })
    
    print('Deployed job contract')
  
  time.sleep(30)
  
  with open(__file__ + '/../build/boc/contract-offer.boc', 'rb') as oc:
    ocs, oca = code_to_init_and_addr(oc.read())
    
    print('Deploying offer contract to', oca.to_string(True, True, True))
    
    query = wallet.create_transfer_message(
      oca, to_nano(0.03, 'ton'), seqno+1, state_init=ocs
    )
    requests.post('https://testnet.tonapi.io/v1/send/boc', json={
      'boc': base64.b64encode(query['message'].to_boc(False)).decode('ascii')
    })
    
    print('Deployed offer contract')
  
except:
  traceback.print_exc()
finally:
  input('...')
