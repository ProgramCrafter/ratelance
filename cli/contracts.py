from bcutils import input_address, load_account
from colors import h, nh, b, nb
from signing import sign_send

from tonsdk.boc import Builder, Cell
from tonsdk.utils import Address
import nacl.signing

from base64 import b16decode, b16encode
import hashlib



def serialize_signed_data(job: Address, bottom: int, upper: int) -> bytes:
  b = Builder()
  b.store_bytes(b16decode('FFFF726C3A3A6A6F623A3A7630'))
  b.store_uint(0, 5)
  b.store_address(job)
  b.store_uint(bottom, 64)
  b.store_uint(upper, 64)
  return b.end_cell().bytes_hash()


def sign_pay_proposal(job: Address, bottom: int, upper: int, role: int, key_id: str, keyring) -> Cell:
  key = keyring.keys_info[key_id]
  secret_key_obj = nacl.signing.SigningKey(key['secret'])
  to_sign = serialize_signed_data(job, bottom, upper)
  signature = secret_key_obj.sign(to_sign)[:512//8]
  print(signature, len(signature))
  
  b = Builder()
  b.store_uint(role, 2)
  b.store_bytes(signature)
  b.store_uint(bottom, 64)
  b.store_uint(upper, 64)
  return b.end_cell()


def double_sign_proposal(job: Address, bottom: int, upper: int, key_id1: str, key_id2: str, keyring, role1=0, role2=1) -> Cell:
  b = Builder()
  b.store_uint(0x000000BB, 32)
  b.store_ref(sign_pay_proposal(job, bottom, upper, role1, key_id1, keyring))
  b.store_ref(sign_pay_proposal(job, bottom, upper, role2, key_id2, keyring))
  return b.end_cell()


def upsign_proposal(job: Address, bottom: int, upper: int, key_id: str, keyring, role: int, proposal: Cell) -> Cell:
  b = Builder()
  b.store_uint(0x000000BB, 32)
  b.store_ref(proposal)
  b.store_ref(sign_pay_proposal(job, bottom, upper, role, key_id, keyring))
  return b.end_cell()


def close_job_with(job: Address, proposal: Cell):
  sign_send([
    (job, None, proposal, 5*10**7)
  ], 'closing job ' + job.to_string(True, True, True))


def load_job_keys_triple(job: Address) -> (bytes, bytes, bytes):
  acc = load_account(job.to_string(True, True, True))
  assert acc['status'] == 'active'
  
  d = Cell.one_from_boc(b16decode(acc['data'].upper())).begin_parse()
  flag = d.load_uint(2)
  assert flag == 2
  
  d.load_msg_addr()
  d.load_msg_addr()
  d.skip_bits(64)
  d.load_ref()
  d.load_ref()
  keys = d.load_ref().begin_parse()
  d.end_parse()
  
  p = keys.load_bytes(32)
  w = keys.load_bytes(32)
  r = keys.load_bytes(32)
  keys.end_parse()
  return (p, w, r)


def check_intersect(limits_a: tuple[int, int], proposal_plus_limits: tuple[Cell, int, int]) -> bool:
  return max(limits_a[0], limits_b[1]) <= min(limits_a[1], limits_b[2])


def check_negotiate_suggestions(job: Address, p: bytes, w: bytes, r: bytes, skip_role: int):
  for tx in load_transactions(job.to_string(True, True, True)):
    try:
      body = Cell.one_from_boc(b64decode(tx['in_msg']['msg_data'])).begin_parse()
      if body.preload_uint(32) != 0x4bed4ee8: continue
      
      proposal_cell = body.load_ref()
      proposal_part = proposal_cell.begin_parse()
      role = proposal_part.load_uint(2)
      if role == 3:
        print('* someone claims that TON validators have voted; check TON config param 1652841508')
        continue
      if role == skip_role:
        # this can be our own negotiation message
        continue
      
      check_key_bytes = ((p, w, r))[role]
      check_key_obj = nacl.signing.VerifyKey(check_key_bytes)
      
      signature = proposal_part.load_bytes(512 // 8)
      pay_bottom = proposal_part.load_uint(64)
      pay_upper  = proposal_part.load_uint(64)
      
      check_key_obj.verify(serialize_signed_data(job, pay_bottom, pay_upper),
                           signature)
      
      yield [proposal_cell, pay_bottom, pay_upper]
    except Exception as exc:
      print(f'{b}Error while processing contract payment negotiation:{nb}', repr(exc))


def is_key_available(i: int, key: bytes, keyring) -> bool:
  key_hex = b16encode(key).decode('ascii')
  key_armored = 'pub:ed25519:vk:' + key_hex
  key_id = hashlib.sha256(key_armored.encode('ascii')).hexdigest()[::8]
  if key_id in keyring.keys_info:
    return (i, key_id)
  return None


def check_available_roles_keyids(p: bytes, w: bytes, r: bytes, keyring):
  return list(filter(None, [is_key_available(i, k, keyring) for i,k in enumerate((p,w,r))]))


def process_contract_cmd(command: str, keyring):
  if command == 'ct':
    print(f'{h}not implemented:{nh} \'ct\'')
  elif command == 'cn':
    job = input_address(f'{b}Job address:{nb} ')
    (poster_key, worker_key, ratelance_key) = load_job_keys_triple(job)
    available_keys = check_available_roles_keyids(poster_key, worker_key, ratelance_key, keyring)
    
    if len(available_keys) > 1:
      print('We have keys of two sides. Proceeding to contract closing.')
      upper = int(float(input(f'{b}TON to give to freelancer (upper limit):{nb} ')) * 1e9)
      bottom = int(float(input(f'{b}TON to give to freelancer (bottom limit):{nb} ')) * 1e9)
      
      role1, key1 = available_keys[0]
      role2, key2 = available_keys[1]
      
      close_job_with(job, double_sign_proposal(
        job, bottom, upper, key1, key2, keyring, role1, role2
      ))
    else:
      print('We have key of single party. Looking for negotiation requests.')
      skip_role = available_keys[0][0]
      
      # (proposal_cell, pay_bottom, pay_upper)
      negotiations = list(check_negotiate_suggestions(job, poster_key, worker_key, ratelance_key, skip_role))
      
      if negotiations:
        min_fl = min(n[1] for n in negotiations) / 1e9
        max_fl = max(n[2] for n in negotiations) / 1e9
        print(f'There are suggestions to give {min_fl}..{max_fl} TON to freelancer.')
        upper = int(float(input(f'{b}TON you want to give to freelancer (upper limit):{nb} ')) * 1e9)
        bottom = int(float(input(f'{b}TON you want to give to freelancer (bottom limit):{nb} ')) * 1e9)
        
        for n in negotiations:
          if check_intersect((bottom, upper), n):
            print('Found matching suggestion. Building message with two signatures...')
            p = upsign_proposal(job, bottom, upper, available_keys[0][1], keyring, skip_role, n[0])
            close_job_with(job, p)
            return
        else:
          print('No matching suggestion. Proceeding to sending negotiation request to other party.')
      else:
        upper = int(float(input(f'{b}TON you want to give to freelancer (upper limit):{nb} ')) * 1e9)
        bottom = int(float(input(f'{b}TON you want to give to freelancer (bottom limit):{nb} ')) * 1e9)
      
      p = sign_pay_proposal(job, bottom, upper, skip_role, available_keys[0][1], keyring)
      msg = Builder()
      msg.store_uint(0x4bed4ee8, 32)
      msg.store_ref(p)
      sign_send([
        (job, None, msg.end_cell(), 2)
      ], 'negotiating payment for job ' + job.to_string(True, True, True))
    
  else:
    print(f'{b}not implemented:{nb} {repr(command)}')
