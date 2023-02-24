# Modified version of _slice.py from fork of tonsdk library:
# https://github.com/devdaoteam/tonsdk/blob/e3d6451e50a46d984e7fec1c52d1d32290781da5/tonsdk/boc/_slice.py
# Original code is licensed under Apache-2.0 License.

import bitarray

from tonsdk.boc import Cell
from tonsdk.utils import Address



class Slice:
  '''Slice like an analog of slice in FunC. Used only for reading.'''
  def __init__(self, cell: Cell):
    self.bits = bitarray.bitarray()
    self.bits.frombytes(cell.bits.array)
    self.bits = self.bits[:cell.bits.cursor]
    self.refs = cell.refs
    self.ref_offset = 0

  def __len__(self):
    return len(self.bits)

  def __repr__(self):
    return hex(int(self.bits.to01(), 2))[2:].upper()

  def is_empty(self) -> bool:
    return len(self.bits) == 0

  def end_parse(self):
    '''Throws an exception if the slice is not empty.'''
    if not self.is_empty() or self.ref_offset != len(self.refs):
      raise Exception('Upon .end_parse(), slice is not empty.')

  def load_bit(self) -> int:
    '''Loads single bit from the slice.'''
    bit = self.bits[0]
    del self.bits[0]
    return bit

  def preload_bit(self) -> int:
    return self.bits[0]

  def load_bits(self, bit_count: int) -> bitarray.bitarray:
    bits = self.bits[:bit_count]
    del self.bits[:bit_count]
    return bits

  def preload_bits(self, bit_count: int) -> bitarray.bitarray:
    return self.bits[:bit_count]

  def skip_bits(self, bit_count: int):
    del self.bits[:bit_count]

  def load_uint(self, bit_length: int) -> int:
    value = self.bits[:bit_length]
    del self.bits[:bit_length]
    return int(value.to01(), 2)

  def preload_uint(self, bit_length: int) -> int:
    value = self.bits[:bit_length]
    return int(value.to01(), 2)

  def load_bytes(self, bytes_count: int) -> bytes:
    length = bytes_count * 8
    value = self.bits[:length]
    del self.bits[:length]
    return value.tobytes()

  def load_int(self, bit_length: int) -> int:
    if bit_length == 1:
      # if num is -1 then bit is 1. if 0 then 0. see _bit_string.py
      return - self.load_bit()
    else:
      is_negative = self.load_bit()
      value = self.load_uint(bit_length - 1)
      if is_negative == 1:
        # ones complement
        return - (2 ** (bit_length - 1) - value)
      else:
        return value

  def preload_int(self, bit_length: int) -> int:
    tmp = self.bits
    value = self.load_int(bit_length)
    self.bits = tmp
    return value

  def load_msg_addr(self) -> Address:
    '''Loads contract address from the slice.
    May return None if there is a zero-address.'''
    # TODO: support for external addresses
    if self.load_uint(2) == 0:
      return None
    self.load_bit()  # anycast
    workchain_id = hex(self.load_int(8))[2:]
    hashpart = hex(self.load_uint(256))[2:]
    return Address(workchain_id + ':' + hashpart)

  def load_coins(self) -> int:
    '''Loads an amount of coins from the slice. Returns nanocoins.'''
    length = self.load_uint(4)
    if length == 0:  # 0 in length means 0 coins
      return 0
    else:
      return self.load_uint(length * 8)

  def load_grams(self) -> int:
    '''Loads an amount of coins from the slice. Returns nanocoins.'''
    return self.load_coins()

  def load_string(self, length: int = 0) -> str:
    '''Loads string from the slice.
    If length is 0, then loads string until the end of the slice.'''
    if length == 0:
      length = len(self.bits) // 8
    return self.load_bytes(length).decode('utf-8')

  def load_ref(self) -> Cell:
    '''Loads next reference cell from the slice.'''
    ref = self.refs[self.ref_offset]
    self.ref_offset += 1
    return ref

  def preload_ref(self) -> Cell:
    return self.refs[self.ref_offset]

  def load_dict(self) -> Cell:
    '''Loads dictionary like a Cell from the slice.
    Returns None if the dictionary was null().'''
    not_null = self.load_bit()
    if not_null:
      return self.load_ref()
    else:
      return None

  def preload_dict(self) -> Cell:
    not_null = self.preload_bit()
    if not_null:
      return self.preload_ref()
    else:
      return None

  def skip_dict(self):
    self.load_dict()
