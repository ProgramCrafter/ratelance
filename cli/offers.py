from bcutils import decode_text, encode_text, load_transactions, shorten_escape
from signing import retrieve_auth_wallet, sign_send
from colors import h, nh, b, nb
from keyring import Keyring 

from base64 import b64decode, b16encode
import traceback

from tonsdk.boc import Builder, Cell
from tonsdk.utils import Address
from tslice import Slice



def offer_data_init(job: str, worker: Address, stake: int, desc: Cell,
                    key: int, short_job_hash: int) -> Cell:
  di = Builder()
  di.store_uint(0, 2)
  di.store_address(job)
  di.store_address(Address(worker))
  di.store_uint(stake, 64)
  di.store_ref(desc)
  di.store_uint(key, 256)
  di.store_uint(short_job_hash, 160)
  return di.end_cell()


def offer_state_init(job: str, worker: Address, stake: int, desc: Cell,
                     key: int, short_job_hash: int) -> Cell:
  with open(__file__ + '/../assets/contract-offer.boc', 'rb') as f:
    code = Cell.one_from_boc(f.read())
  
  si = Builder()
  si.store_uint(6, 5)
  si.store_ref(code)
  si.store_ref(offer_data_init(job, worker, stake, desc, key, short_job_hash))
  return si.end_cell()


def analytic_msg(offer: Address, stake: int, desc: Cell,
                 key: int, short_job_hash: int) -> Cell:
  am = Builder()
  am.store_address(offer)
  am.store_uint(stake, 64)
  am.store_ref(desc)
  am.store_uint(key, 256)
  am.store_uint(short_job_hash, 160)
  return am.end_cell()


def load_offers(job: str, start_lt=None):
  if start_lt: raise Exception('loading specific offers not supported')
  
  for tx in load_transactions(job, start_lt=start_lt):
    try:
      if tx['in_msg']['value'] != 1: continue
      
      worker = Address(tx['in_msg']['source']['address'])
      body = Cell.one_from_boc(b64decode(tx['in_msg']['msg_data'])).begin_parse()
      offer = body.load_msg_addr()
      stake = body.load_uint(64)
      desc = body.load_ref()
      desc_text = decode_text(desc)
      key = body.load_uint(256)
      shjh = body.load_uint(160)
      
      if offer.hash_part != offer_state_init(job, worker, stake, desc, key, shjh).bytes_hash():
        print(f'{b}Found notification with invalid offer address:{nb}', offer.to_string())
        print(f'* {h}worker:      {nh}{worker.to_string()}')
        print(f'* {h}description: {nh}{repr(desc_text)}')
      else:
        yield (offer.to_string(), worker.to_string(), stake, desc_text)
    except Exception as exc:
      print(f'{b}Failure while processing notification:{nb}', repr(exc))


def show_offers(job: str, start_lt=None, validate_offers=False):
  if validate_offers: raise Exception('validating offers not supported')
  # requires checking whether contract exists and is attached as plugin to worker's wallet
  
  for (offer, worker, stake, desc) in load_offers(job, start_lt):
    oid = offer[40:]
    print(f'Offer [{h}{oid}{nh}] {offer}')
    print(f'- {h}posted by{nh} {worker}')
    print(f'- {h}staked{nh}    {stake/1e9} TON, {h}really available{nh} <unknown>')
    print('-', shorten_escape(desc))

'''
def post_job(value: int, stake: int, desc_text: str, keyring: Keyring, key_id: str):
  print(f'\n{h}Creating new job{nh}', repr(desc_text))
  
  key_info = keyring.keys_info[key_id]
  assert key_info['key_id'] == key_id
  public_key = int.from_bytes(key_info['public'], 'big')
  
  WAY_PROMPT = f'Send via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]/ton link [{h}t{nh}]? '
  while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's', 't'): pass
  
  wallet = None
  poster = None
  
  if auth_way == 't':
    while True:
      try:
        poster = Address(input(f'{b}Your address: {nb}'))
        break
      except KeyboardInterrupt:
        raise
      except Exception:
        pass
  else:
    wallet = retrieve_auth_wallet(auth_way)
    poster = wallet.address.to_string(True, True, True)
  
  desc = encode_text(desc_text)
  si = job_state_init(poster, value, desc, public_key)
  addr = Address('0:' + b16encode(si.bytes_hash()).decode('ascii'))
  am = analytic_msg(addr, value, desc, public_key)
  
  jobs = Address(JOB_NOTIFICATIONS)
  jobs.is_bounceable = False
  
  print()
  sign_send([
    (addr, si,   Cell(), stake),
    (jobs, None, am,     5*10**7),
  ], 'creating job', auth_way, wallet)
'''

def process_offers_cmd(command, keyring):
  if command == 'ol':
    # TODO: support job IDs instead of addresses
    job = None
    while True:
      try:
        job = Address(input(f'{b}Job address: {nb}'))
        break
      except KeyboardInterrupt:
        raise
      except Exception:
        pass
    
    show_offers(job.to_string())
  # elif command == 'jp':
  #   possible_keys = list(keyring.keys_info.keys())
  #   if len(possible_keys) > 3:
  #     possible_keys_s = '/'.join(possible_keys[:3]) + '/...'
  #   else:
  #     possible_keys_s = '/'.join(possible_keys) or '<nothing available>'
  #   
  #   key_id = input(f'Used key ({possible_keys_s}): ')
  #   value = int(1e9 * float(input('Promised job value (TON): ')))
  #   stake = int(1e9 * float(input('Send stake (TON): ')))
  #   desc_text = input('Job description: ')
  #   
  #   post_job(value, stake, desc_text, keyring, key_id)
  else:
    print(f'{b}not implemented:{nb} {repr(command)}')