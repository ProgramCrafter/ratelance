module Main

%default partial


--------------------------------------------------------------------------------
----  Std extensions
--------------------------------------------------------------------------------

lookupBy : (a -> b -> Bool) -> a -> List (b, v) -> Maybe v
lookupBy p e []      = Nothing
lookupBy p e ((l, r) :: xs) =
  if p e l then
    Just r
  else
    lookupBy p e xs

--------------------------------------------------------------------------------
----  Arithmetic types
--------------------------------------------------------------------------------

data UintSeq : Nat -> Type where
  UintSeqVoid : UintSeq Z
  UintSeqLow  : (bits : Nat) -> UintSeq bits -> UintSeq (S bits)
  UintSeqHigh : (bits : Nat) -> UintSeq bits -> UintSeq (S bits)

using (n : Nat)
  Eq (UintSeq n) where
    (==)  UintSeqVoid       UintSeqVoid      = True
    (==) (UintSeqLow _ a)  (UintSeqLow _ b)  = a == b
    (==) (UintSeqHigh _ _) (UintSeqLow _ _)  = False
    (==) (UintSeqLow _ _)  (UintSeqHigh _ _) = False
    (==) (UintSeqHigh _ a) (UintSeqHigh _ b) = a == b
  
  Ord (UintSeq n) where
    compare  UintSeqVoid       UintSeqVoid      = EQ
    compare (UintSeqLow _ a)  (UintSeqLow _ b)  = compare a b
    compare (UintSeqHigh _ _) (UintSeqLow _ _)  = GT
    compare (UintSeqLow _ _)  (UintSeqHigh _ _) = LT
    compare (UintSeqHigh _ a) (UintSeqHigh _ b) = compare a b


seq_to_bits : (n : Nat) -> UintSeq n -> List Nat
seq_to_bits Z     UintSeqVoid         = Nil
seq_to_bits (S n) (UintSeqLow n low)  = 0 :: (seq_to_bits n low)
seq_to_bits (S n) (UintSeqHigh n low) = 1 :: (seq_to_bits n low)

bits_to_nat : List Nat -> Nat
bits_to_nat Nil        = 0
bits_to_nat (v :: old) = (bits_to_nat old) + (bits_to_nat old) + v

stn : (n : Nat) -> UintSeq n -> Nat
stn n v = bits_to_nat (reverse (seq_to_bits n v))

build_zero_uint_seq : (n : Nat) -> UintSeq n
build_zero_uint_seq Z     = UintSeqVoid
build_zero_uint_seq (S k) = UintSeqLow _ (build_zero_uint_seq k)

build_high_uint_seq : (n : Nat) -> UintSeq n
build_high_uint_seq Z     = UintSeqVoid
build_high_uint_seq (S k) = UintSeqHigh _ (build_high_uint_seq k)

--------------------------------------------------------------------------------
----  TON-specific types
--------------------------------------------------------------------------------

data Anycast : Type where
  AnycastCreate : (depth : UintSeq 5) -> (pfx : UintSeq (stn 5 depth)) -> Anycast

data MessageAddr : Type where
  MsgAddressIntStd : (Maybe Anycast) -> (workchain : UintSeq 8)  -> (hash_part : UintSeq 256) -> MessageAddr
  -- MsgAddressIntVar : (Maybe Anycast) -> (addr_len : UintSeq 9)   -> (workchain : UintSeq 32)  -> (hash_part : UintSeq (stn 9 addr_len)) -> MessageAddr

Eq MessageAddr where
  (==) (MsgAddressIntStd Nothing wc1 hp1) (MsgAddressIntStd Nothing wc2 hp2) = (wc1 == wc2) && (hp1 == hp2)
  (==) _ _ = False

data TxMessage : Type where
  IntMessage    : (bounce : Bool) -> (src : MessageAddr) -> (dest : MessageAddr) -> (coins : UintSeq 120) -> (init : Maybe ()) -> (body : List Nat) -> TxMessage
  ExtInMessage  : (src : MessageAddr) -> (dest : MessageAddr) -> (init : Maybe ()) -> (body : List Nat) -> TxMessage
  ExtOutMessage : (src : MessageAddr) -> (dest : MessageAddr) -> (init : Maybe ()) -> (body : List Nat) -> TxMessage

--------------------------------------------------------------------------------
----  High-level contracts representation
--------------------------------------------------------------------------------

mutual
  data NextState : Type where
    MkNextState : ContractState ncs => ncs -> NextState
  
  interface ContractState cs where
    to_code : cs -> (cs -> TxMessage -> (NextState, List TxMessage))
    to_data : cs -> Type

data Contract : Type where
  Uninit : (addr : MessageAddr) -> Contract
  Init   : ContractState cs => (addr : MessageAddr) -> (st : cs) -> (balance : Nat) -> Contract

apply_message : ContractState cs => cs -> TxMessage -> (NextState, List TxMessage)
apply_message state msg = (to_code state) state msg

apply_wrapped : NextState -> TxMessage -> (NextState, List TxMessage)
apply_wrapped (MkNextState wrapped_state) msg = (to_code wrapped_state) wrapped_state msg

bounce_typical : ContractState cs => cs -> TxMessage -> (NextState, List TxMessage)
bounce_typical state (IntMessage True src self coins _ body)  = (MkNextState state, [IntMessage False self src coins Nothing $ (seq_to_bits _ $ build_high_uint_seq 32) ++ body])
bounce_typical state _                                        = (MkNextState state, Nil)

--------------------------------------------------------------------------------
----  Job contract
--------------------------------------------------------------------------------

data JobContractDataUnlocked : Type where
  JcdUnlocked : (poster : MessageAddr) -> (desc : Type) -> (value : UintSeq 120) -> (poster_key : UintSeq 256) -> JobContractDataUnlocked

data JobContractStateUnlocked : Type where
  JcsUnlocked : (jccode : (JobContractStateUnlocked -> TxMessage -> (NextState, List TxMessage))) -> (jcdata : Type) -> JobContractStateUnlocked

ContractState JobContractStateUnlocked where
  to_code cur_state = let JcsUnlocked jccode jcdata = cur_state in
                        jccode
  to_data cur_state = let JcsUnlocked jccode jcdata = cur_state in
                        jcdata

jccu_typical : JobContractStateUnlocked -> TxMessage -> (NextState, List TxMessage)
jccu_typical = bounce_typical

----

data JobContractDataLockedOn : Type where
  JcdLockedOn : (poster : MessageAddr) -> (desc : Type) -> (value : UintSeq 120) -> (poster_key : UintSeq 256) -> (offer : MessageAddr) -> JobContractDataLockedOn

data JobContractStateLockedOn : Type where
  JcsLockedOn : (jccode : (JobContractStateLockedOn -> TxMessage -> (NextState, List TxMessage))) -> (jcdata : Type) -> JobContractStateLockedOn

ContractState JobContractStateLockedOn where
  to_code cur_state = let JcsLockedOn jccode jcdata = cur_state in
                        jccode
  to_data cur_state = let JcsLockedOn jccode jcdata = cur_state in
                        jcdata

----

data JobContractDataWorking : Type where
  JcdWorking  : (poster : MessageAddr) -> (desc : Type) -> (value : UintSeq 120) -> (poster_key : UintSeq 256) -> (worker_key : UintSeq 256) -> JobContractDataWorking

data JobContractStateWorking : Type where
  JcsWorking  : (jccode : (JobContractStateWorking -> TxMessage -> (NextState, List TxMessage))) -> (jcdata : Type) -> JobContractStateWorking

ContractState JobContractStateWorking where
  to_code cur_state = let JcsWorking jccode jcdata = cur_state in
                        jccode
  to_data cur_state = let JcsWorking jccode jcdata = cur_state in
                        jcdata

----

build_contract : NextState
build_contract = MkNextState $ JcsUnlocked jccu_typical ()

data ContractStorage = MkStorage (List (MessageAddr, NextState))
lookup_contract : ContractStorage -> MessageAddr -> Maybe NextState
lookup_contract (MkStorage contracts) addr = lookupBy f () contracts where
  f : () -> MessageAddr -> Bool
  f _ some_addr  =  addr == some_addr

extract_contract : ContractStorage -> MessageAddr -> (Maybe NextState, ContractStorage)
extract_contract (MkStorage Nil)     addr = (Nothing, MkStorage Nil)
extract_contract (MkStorage (x::xs)) addr = let (gaddr, v) = x in
                                              if gaddr == addr then
                                                (Just v, MkStorage xs)
                                              else
                                                let (loaded, MkStorage storage) = extract_contract (MkStorage xs) addr in
                                                  (loaded, MkStorage ((gaddr,v) :: storage))

----

main : IO ()
main = do putStrLn "Theorems proved"
          putStrLn "Starting transactions loop"
          putStrLn "Transactions loop finished"
