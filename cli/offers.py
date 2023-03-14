from .bcutils import decode_text, encode_text, load_transactions, shorten_escape, input_address, load_account
from .signing import retrieve_auth_wallet, sign_send, sign_install_plugin, sign_uninstall_plugin
from .colors import h, nh, b, nb
from .keyring import Keyring 

from base64 import b64decode, b16decode, b16encode
import traceback
import time

from tonsdk.boc import Builder, Cell
from tonsdk.utils import Address
from .tslice import Slice



def offer_data_init(job: str, worker: Address, stake: int, desc: Cell,
                    key: int, short_job_hash: int) -> Cell:
  di = Builder()
  di.store_uint(0, 2)
  di.store_address(Address(job))
  di.store_address(worker)
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
  am.store_uint(0x18ceb1bf, 32)
  am.store_address(offer)
  am.store_uint(stake, 64)
  am.store_ref(desc)
  am.store_uint(key, 256)
  am.store_uint(short_job_hash, 160)
  return am.end_cell()


def load_offers(job: str, start_lt=None):
  if start_lt: raise Exception('loading specific offers not supported')
  
  job_data = Cell.one_from_boc(b16decode(load_account(job)['data'].upper()))
  job_hash = int.from_bytes(job_data.bytes_hash(), 'big') & ((1 << 160) - 1)
  
  if job_data.begin_parse().load_uint(2) != 0:
    print(f'{b}[job not in unlocked state]{nb}')
  
  for tx in load_transactions(job, start_lt=start_lt):
    try:
      if tx['in_msg']['value'] != 1: continue
      
      worker = Address(tx['in_msg']['source']['address'])
      body = Cell.one_from_boc(b64decode(tx['in_msg']['msg_data'])).begin_parse()
      
      if body.preload_uint(32) not in (0x18ceb1bf, 0x4bed4ee8):
        print(f'\n{b}* legacy offer notification [without TL-B tag]{nb}')
        assert tx['hash'] in (
          '4109a9bf38f7376acdb013ff95e33ebb5112c00ebd9d93a348361522400b5783',
          '8fb9cb7532a8d6a710106d1c346f99bdd22a2d74480858956ecc19a02e1dfd8d',
          'a598c47a792ceccb9e26b2cd5cc73c7a6024dae12f24ae20747182966b407b65',
        )
      else:
        body.skip_bits(32)
      
      offer = body.load_msg_addr()
      stake = body.load_uint(64)
      desc = body.load_ref()
      desc_text = decode_text(desc)
      key = body.load_uint(256)
      shjh = body.load_uint(160)
      
      hash_up_to_date = shjh == job_hash
      
      if offer.hash_part != offer_state_init(job, worker, stake, desc, key, shjh).bytes_hash():
        print(f'{b}Found notification with invalid offer address:{nb}', offer.to_string())
        print(f'* {h}worker:      {nh}{worker.to_string()}')
        print(f'* {h}description: {nh}{repr(desc_text)}')
      else:
        yield (offer.to_string(True, True, True), worker.to_string(True, True, True),
               stake, desc_text, hash_up_to_date)
    except Exception as exc:
      print(f'{b}Failure while processing notification:{nb}', repr(exc))


def show_offers(job: str, start_lt=None, validate_offers=False):
  if validate_offers: raise Exception('validating offers not supported')
  # requires checking whether contract exists and is attached as plugin to worker's wallet
  
  for (offer, worker, stake, desc, hash_up_to_date) in load_offers(job, start_lt):
    oid = offer[40:]
    print(f'\nOffer [{h}{oid}{nh}] {offer}')
    print(f'- {h}posted by{nh} {worker}')
    print(f'- {h}staked{nh}    {stake/1e9} TON, {h}really available{nh} <unknown>')
    print(f'- {h}hash{nh}      {"" if hash_up_to_date else "not "}up to date')
    print('-', shorten_escape(desc))


def post_offer(job: str, stake: int, desc_text: str, shjh: int, keyring: Keyring, key_id: str):
  print(f'\n{h}Creating new offer{nh}', repr(desc_text))
  print('You will have to use v4 wallet, because offer is a plugin.')
  
  key_info = keyring.keys_info[key_id]
  assert key_info['key_id'] == key_id
  public_key = int.from_bytes(key_info['public'], 'big')
  
  WAY_PROMPT = f'Send via mnemonic [{h}m{nh}]/wallet seed [{h}s{nh}]? '
  while (auth_way := input(WAY_PROMPT).lower()) not in ('m', 's'): pass
  
  wallet = retrieve_auth_wallet(auth_way, plugin_only=True)
  worker = wallet.address.to_string(True, True, True)
  
  desc = encode_text(desc_text)
  si = offer_state_init(job, wallet.address, stake, desc, public_key, shjh)
  addr = Address('0:' + b16encode(si.bytes_hash()).decode('ascii'))
  am = analytic_msg(addr, stake, desc, public_key, shjh)
  
  print()
  sign_install_plugin(si, 5*10**7, 'creating offer', wallet)
  print('... please, wait for blockchain update (30s) ...')
  time.sleep(30)
  print()
  sign_send([(job, None, am, 1)], 'notifying job poster', auth_way, wallet)


def revoke_offer(offer: str):
  sign_uninstall_plugin(offer, 'revoking offer')


def process_offers_cmd(command, keyring):
  if command == 'ol':
    # TODO: support job IDs instead of addresses
    job = input_address(f'{b}Job address: {nb}')
    
    show_offers(job.to_string())
  elif command == 'op':
    possible_keys = list(keyring.keys_info.keys())
    if len(possible_keys) > 3:
      possible_keys_s = '/'.join(possible_keys[:3]) + '/...'
    else:
      possible_keys_s = '/'.join(possible_keys) or '<nothing available>'
    
    key_id = input(f'Used key ({possible_keys_s}): ')
    job = input_address(f'{b}Job address: {nb}')
    stake = int(1e9 * float(input('Staked value (TON): ')))
    desc_text = input('Offer description: ')
    
    job_data = Cell.one_from_boc(b16decode(
      load_account(job.to_string())['data'].upper()
    ))
    assert job_data.begin_parse().load_uint(2) == 0
    job_hash = int.from_bytes(job_data.bytes_hash(), 'big') & ((1 << 160) - 1)
    
    post_offer(job, stake, desc_text, job_hash, keyring, key_id)
  elif command == 'or':
    revoke_offer(input_address(f'{b}Offer address: {nb}').to_string(True, True, True))
  else:
    print(f'{b}not implemented:{nb} {repr(command)}')