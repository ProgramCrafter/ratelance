from tonsdk.boc import Builder, Cell
import requests


def load_transactions(address, start_lt):
  return requests.get(
    f'https://tonapi.io/v1/blockchain/getTransactions?account={address}&limit=100'
  ).json()['transactions']


def decode_text(cell: Cell) -> str:
  a = ''
  s = cell.begin_parse()
  if s.is_empty():            return ''
  if s.preload_uint(32) == 0: s.skip_bits(32)
  a += s.load_bytes(len(s) // 8).decode('utf-8')
  while s.refs:
    s = s.load_ref().begin_parse()
    a += s.load_bytes(len(s) // 8).decode('utf-8')
  return a


def encode_text(a) -> Cell:
  if isinstance(a, str):
    s = a.encode('utf-8')
  else:
    s = a
  
  b = Builder()
  b.store_bytes(s[:127])
  if len(s) > 127:
    b.store_ref(encode_text(s[127:]))
  return b.end_cell()


def shorten_escape(s: str, indent=2) -> str:
  s = s.replace('\x1b', '').replace('\r', '')
  lines = s.split('\n')
  if len(lines) > 4:
    lines = lines[:3] + ['...']
  if lines:
    lines = [lines[0]] + [' ' * indent + line for line in lines[1:]]
  return '\n'.join(lines)
