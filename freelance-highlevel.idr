module Main

%default partial


--------------------------------------------------------------------------------
----  Arithmetic types
--------------------------------------------------------------------------------

data UintSeq : Nat -> Type where
  UintSeqVoid : UintSeq Z
  UintSeqLow  : (bits : Nat) -> UintSeq bits -> UintSeq (S bits)
  UintSeqHigh : (bits : Nat) -> UintSeq bits -> UintSeq (S bits)

seq_to_bits : (n : Nat) -> UintSeq n -> List Nat
seq_to_bits Z     UintSeqVoid         = Nil
seq_to_bits (S n) (UintSeqLow n low)  = 0 :: (seq_to_bits n low)
seq_to_bits (S n) (UintSeqHigh n low) = 1 :: (seq_to_bits n low)

bits_to_nat : List Nat -> Nat
bits_to_nat Nil        = 0
bits_to_nat (v :: old) = (bits_to_nat old) + (bits_to_nat old) + v

stn : (n : Nat) -> UintSeq n -> Nat
stn n v = bits_to_nat (reverse (seq_to_bits n v))

--------------------------------------------------------------------------------
----  TON-specific types
--------------------------------------------------------------------------------

data Anycast : Type where
  AnycastCreate : (depth : UintSeq 5) -> (pfx : UintSeq (stn 5 depth)) -> Anycast

data MessageAddr : Type where
  MsgAddressIntStd : (Maybe Anycast) -> (workchain : UintSeq 8)  -> (hash_part : UintSeq 256) -> MessageAddr
  -- MsgAddressIntVar : (Maybe Anycast) -> (addr_len : UintSeq 9)   -> (workchain : UintSeq 32)  -> (hash_part : UintSeq (stn 9 addr_len)) -> MessageAddr

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

apply_message : ContractState cs => cs -> TxMessage -> (NextState, List TxMessage)
apply_message state msg = (to_code state) state msg


apply_message_jcsu_wrapper : JobContractStateUnlocked -> TxMessage -> (NextState, List TxMessage)
apply_message_jcsu_wrapper state msg = apply_message state msg

build_hang_contract : JobContractStateUnlocked
build_hang_contract = JcsUnlocked apply_message_jcsu_wrapper ()

build_zero_uint_seq : (n : Nat) -> UintSeq n
build_zero_uint_seq Z     = UintSeqVoid
build_zero_uint_seq (S k) = UintSeqLow _ (build_zero_uint_seq k)

build_sample_addr : MessageAddr
build_sample_addr = MsgAddressIntStd Nothing (build_zero_uint_seq 8) (build_zero_uint_seq 256)

build_sample_msg : TxMessage
build_sample_msg  = IntMessage False build_sample_addr build_sample_addr (build_zero_uint_seq 120) Nothing Nil


hang : (NextState, List TxMessage)
hang = apply_message build_hang_contract build_sample_msg

test_to_string : (NextState, List TxMessage) -> String
test_to_string (new_state, messages) = show (length messages)

----

main : IO ()
main = do putStrLn "Theorems proved"
          putStrLn (test_to_string hang)
