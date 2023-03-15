from .bcutils import decode_text, encode_text, load_transactions, shorten_escape, input_address, load_account
from .signing import retrieve_auth_wallet, sign_send
from .colors import h, nh, b, nb
from .keyring import Keyring 

from base64 import b64decode, b16decode, b16encode
import traceback
import hashlib

from tonsdk.boc import Builder, Cell
from tonsdk.utils import Address
from .tslice import Slice



JOB_NOTIFICATIONS = 'EQA__RATELANCE_______________________________JvN'


def job_data_init(poster: str, value: int, desc: Cell, key: int) -> Cell:
  di = Builder()
  di.store_uint(0, 2)
  di.store_address(Address(poster))
  di.store_uint(value, 64)
  di.store_ref(desc)
  di.store_uint(key, 256)
  return di.end_cell()


def job_state_init(poster: str, value: int, desc: Cell, key: int) -> Cell:
  with open(__file__ + '/../assets/contract-job.boc', 'rb') as f:
    code = Cell.one_from_boc(f.read())
  
  si = Builder()
  si.store_uint(6, 5)
  si.store_ref(code)
  si.store_ref(job_data_init(poster, value, desc, key))
  return si.end_cell()


def analytic_msg(job: Address, value: int, desc: Cell, key: int) -> Cell:
  am = Builder()
  am.store_uint(0x130850fc, 32)
  am.store_address(job)
  am.store_uint(value, 64)
  am.store_ref(desc)
  am.store_uint(key, 256)
  return am.end_cell()


def load_jobs(start_lt=None, custom_notif_addr=None):
  if start_lt: raise Exception('loading specific jobs not supported')
  
  notif = custom_notif_addr or JOB_NOTIFICATIONS
  for tx in load_transactions(notif, start_lt=start_lt):
    try:
      body = Cell.one_from_boc(b64decode(tx['in_msg']['msg_data'])).begin_parse()
      
      if body.preload_uint(32) != 0x130850fc:
        print(f'\n{b}* legacy job notification [without TL-B tag]{nb}')
        assert tx['hash'] in (
          '155ccfdc282660413ada2c1b71ecbd5935db7afd40c82d7b36b8502fea064b8a',
          'f2c76d3ea82e6147887320a71b359553f99cb176a521d63081facfb80a183dbf',
        )
      else:
        body.load_uint(32)
      
      job = body.load_msg_addr()
      poster = Address(tx['in_msg']['source']['address']).to_string(True, True, True)
      value = body.load_uint(64)
      desc = body.load_ref()
      desc_text = decode_text(desc)
      poster_key = body.load_uint(256)
      
      # TODO: skip notifications with value < 0.05 TON
      
      if job.hash_part != job_state_init(poster, value, desc, poster_key).bytes_hash():
        print(f'{b}Found notification with invalid job address:{nb}', job.to_string())
        print(f'* {h}poster:      {nh}{poster}')
        print(f'* {h}description: {nh}{shorten_escape(desc_text)}')
      else:
        yield (job.to_string(True, True, True), poster, value, desc_text)
    except Exception as exc:
      print(f'{b}Failure while processing notification:{nb}', repr(exc))


def show_jobs(start_lt=None, custom_notif_addr=None, validate_jobs=False):
  if validate_jobs: raise Exception('validating jobs not supported')
  
  for (job, poster, value, desc) in load_jobs(start_lt, custom_notif_addr):
    jid = job[40:]
    print(f'Order [{h}{jid}{nh}] {job}')
    print(f'- {h}posted by{nh} {poster}')
    print(f'- {h}promising{nh} {value/1e9} TON, {h}staked{nh} <unknown>')
    print('-', shorten_escape(desc))


def post_job(value: int, stake: int, desc_text: str, keyring: Keyring, key_id: str):
  print(f'\n{h}Creating new job{nh}', repr(desc_text))
  
  if not key_id.strip() and len(keyring.keys_info) == 1:
    key_id = list(keyring.keys_info.keys())[0]
  
  key_info = keyring.keys_info[key_id]
  assert key_info['key_id'] == key_id
  public_key = int.from_bytes(key_info['public'], 'big')
  
  WAY_PROMPT = f'Send via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]/ton link [{h}t{nh}]? '
  while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's', 't'): pass
  
  if auth_way == 't':
    wallet = None
    poster = input_address(f'{b}Your address: {nb}')
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


def delegate_job(job: str, offer_addr: str):
  msg = Builder()
  msg.store_uint(0x000000AC, 32)
  msg.store_ref(Cell())
  msg.store_address(Address(offer_addr))
  
  sign_send([(Address(job), None, msg.end_cell(), 10**9)], 'delegating job')


def public_key_desc(key: bytes, keyring) -> str:
  key_hex = b16encode(key).decode('ascii')
  key_armored = 'pub:ed25519:vk:' + key_hex
  key_id = hashlib.sha256(key_armored.encode('ascii')).hexdigest()[::8]
  not_present = 'not ' if key_id not in keyring.keys_info else ''
  return f'{key_hex} ({key_id}, {h}{not_present}present{nh} in local keyring)'


def show_job(job: str, keyring):
  acc = load_account(job)
  
  if acc['status'] != 'active':
    print('* contract', acc['status'])
    return
  
  d = Cell.one_from_boc(b16decode(acc['data'].upper())).begin_parse()
  flag = d.load_uint(2)
  
  if flag == 0:
    print(f'* job {h}waiting for offers{nh}')
    print(f'- {h}posted by {nh}', d.load_msg_addr().to_string(True, True, True))
    print(f'- {h}promising {nh}', d.load_uint(64) / 1e9, 'TON')
    print(f'- {h}public key{nh}', public_key_desc(d.load_bytes(32), keyring))
    
    j_desc_text = decode_text(d.load_ref())
    print(f'- {h}job descr {nh}', shorten_escape(j_desc_text, indent=12))
    
    d.end_parse()
  elif flag == 1:
    print(f'* job {h}locked on offer{nh}', d.load_msg_addr().to_string(True, True, True))
    print(f'- {h}posted by {nh}', d.load_msg_addr().to_string(True, True, True))
    print(f'- {h}promising {nh}', d.load_uint(64) / 1e9, 'TON')
    print(f'- {h}public key{nh}', public_key_desc(d.load_bytes(32), keyring))
    
    j_desc_text = decode_text(d.load_ref())
    print(f'- {h}job descr {nh}', shorten_escape(j_desc_text, indent=12))
    
    d.end_parse()
  elif flag == 2:
    print(f'* {h}taken{nh} job')
    print(f'- {h}posted by  {nh}', d.load_msg_addr().to_string(True, True, True))
    print(f'- {h}worker     {nh}', d.load_msg_addr().to_string())
    print(f'- {h}promising  {nh}', d.load_uint(64) / 1e9, 'TON')
    
    j_desc_text = decode_text(d.load_ref())
    print(f'- {h}job descr  {nh}', shorten_escape(j_desc_text, indent=13))
    o_desc_text = decode_text(d.load_ref())
    print(f'- {h}offer descr{nh}', shorten_escape(o_desc_text, indent=13))
    
    keys = d.load_ref().begin_parse()
    print(f'- {h}   poster key{nh}', public_key_desc(keys.load_bytes(32), keyring))
    print(f'- {h}   worker key{nh}', public_key_desc(keys.load_bytes(32), keyring))
    print(f'- {h}Ratelance key{nh}', public_key_desc(keys.load_bytes(32), keyring))
    
    keys.end_parse()
    d.end_parse()
  else:
    print('* broken job contract')


def process_jobs_cmd(command, keyring):
  if command == 'jl':
    show_jobs()
  elif command == 'jp':
    possible_keys = list(keyring.keys_info.keys())
    if len(possible_keys) > 3:
      possible_keys_s = '/'.join(possible_keys[:3]) + '/...'
    else:
      possible_keys_s = '/'.join(possible_keys) or '<nothing available>'
    
    key_id = input(f'Used key ({possible_keys_s}): ')
    value = int(1e9 * float(input('Promised job value (TON): ')))
    stake = int(1e9 * float(input('Send stake (TON): ')))
    desc_text = input('Job description: ')
    
    post_job(value, stake, desc_text, keyring, key_id)
  elif command == 'jd':
    job   = input_address('Job address:   ')
    offer = input_address('Offer address: ')
    
    delegate_job(job, offer)
  elif command == 'ji':
    try:
      show_job(input_address('Job address: ').to_string(True, True, True), keyring)
    except Exception as exc:
      print(f'{b}Invalid job:{nb}', repr(exc))
  else:
    print(f'{b}not implemented:{nb} {repr(command)}')