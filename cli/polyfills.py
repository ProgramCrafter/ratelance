from tonsdk.boc import Cell
from .tslice import Slice

Cell.begin_parse = lambda self: Slice(self)
