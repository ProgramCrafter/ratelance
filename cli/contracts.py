from bcutils import input_address, load_account
from colors import h, nh, b, nb
from signing import sign_send

from tonsdk.boc import Builder, Cell
from tonsdk.utils import Address
import nacl.signing

from base64 import b16decode



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


def double_sign_proposal(job: Address, bottom: int, upper: int, key_id1: str, key_id2: str, keyring) -> Cell:
  b = Builder()
  b.store_uint(0x000000BB, 32)
  b.store_ref(sign_pay_proposal(job, bottom, upper, 0, key_id1, keyring))
  b.store_ref(sign_pay_proposal(job, bottom, upper, 1, key_id2, keyring))
  return b.end_cell()


def close_job_with(job: Address, proposal: Cell):
  sign_send([
    (job, None, proposal, 5*10**7)
  ], 'closing job ' + job.to_string(True, True, True))


def process_contract_cmd(command: str, keyring):
  if command == 'ct':
    print(f'{h}not implemented:{nh} \'ct\'')
  elif command == 'cn':
    job = input_address(f'{b}Job address:{nb} ')
    acc = load_account(job.to_string(True, True, True))
    print(acc)
  elif command == 'cdn':
    job = input_address(f'{b}Job address:{nb} ')
    acc = load_account(job.to_string(True, True, True))
    
    upper = int(float(input(f'{b}TON to give to freelancer (upper limit):{nb} ')) * 1e9)
    lower = int(float(input(f'{b}TON to give to freelancer (lower limit):{nb} ')) * 1e9)
    
    key1 = 'f3433b1a'
    key2 = 'd6de7bf9'
    
    close_job_with(job, double_sign_proposal(
      job, lower, upper, key1, key2, keyring
    ))
  else:
    print(f'{b}not implemented:{nb} {repr(command)}')
