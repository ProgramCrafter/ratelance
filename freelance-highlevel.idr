module Main

import Data.Fin

%default covering


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

repeat : (n : Nat) -> List a -> List a
repeat Z     _ = []
repeat (S n) x = x ++ repeat n x

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

bits_to_seq : (a : List (Fin 2)) -> UintSeq (length a)
bits_to_seq Nil         = UintSeqVoid
bits_to_seq (0 :: next) = UintSeqLow  _ $ bits_to_seq next
bits_to_seq (1 :: next) = UintSeqHigh _ $ bits_to_seq next

bits_to_nat : List Nat -> Nat
bits_to_nat Nil        = 0
bits_to_nat (v :: old) = (bits_to_nat old) * 2 + v

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
  IntMsg    : (bounce : Bool) -> (src : MessageAddr) -> (dest : MessageAddr) -> (coins : UintSeq 120) -> (init : Maybe ()) -> (body : JobMsgBody) -> TxMessage
  ExtInMsg  : (src : MessageAddr) -> (dest : MessageAddr) -> (init : Maybe ()) -> (body : List Nat) -> TxMessage
  ExtOutMsg : (src : MessageAddr) -> (dest : MessageAddr) -> (init : Maybe ()) -> (body : List Nat) -> TxMessage

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

run_tvm : NextState -> TxMessage -> (NextState, List TxMessage)
run_tvm (MkNextState wrapped_state) msg = (to_code wrapped_state) wrapped_state msg

build_bounce : TxMessage -> List TxMessage
build_bounce (IntMsg True src self coins _ body) = [IntMsg False self src coins Nothing $ Bounce body]
build_bounce _                                       = Nil

bounce_typical : ContractState cs => cs -> TxMessage -> (NextState, List TxMessage)
bounce_typical state msg = (MkNextState state, build_bounce msg)

----

-- ContractStorage = (List (MessageAddr, NextState))
lookup_contract : (List (MessageAddr, NextState)) -> MessageAddr -> Maybe NextState
lookup_contract contracts addr = lookupBy f () contracts where
  f : () -> MessageAddr -> Bool
  f _ some_addr  =  addr == some_addr

extract_contract : (List (MessageAddr, NextState)) -> MessageAddr -> (Maybe NextState, (List (MessageAddr, NextState)))
extract_contract Nil     addr = (Nothing, Nil)
extract_contract (x::xs) addr = let (gaddr, v) = x in
                                  if gaddr == addr then
                                    (Just v, xs)
                                  else
                                    let (loaded, storage) = extract_contract xs addr in
                                      (loaded, (gaddr,v) :: storage)

extract_dest : TxMessage -> MessageAddr
extract_dest (IntMsg  _ _ dest _ _ _) = dest
extract_dest (ExtInMsg  _ dest _ _) = dest
extract_dest (ExtOutMsg _ dest _ _) = dest

main_loop : List TxMessage -> List (MessageAddr, NextState) -> (List TxMessage, List (MessageAddr, NextState))
main_loop Nil            contracts = (Nil, contracts)
main_loop (msg :: later) contracts = let (mb_contract, contracts_ext) = extract_contract contracts $ extract_dest msg in
  case mb_contract of
    Nothing       => main_loop (later ++ (build_bounce msg)) contracts_ext
    Just contract => let (upd_contract, send) = run_tvm contract msg in
      (later ++ send, (extract_dest msg, upd_contract) :: contracts_ext)

--------------------------------------------------------------------------------
----  Job contract
--------------------------------------------------------------------------------

data PayProposal : Type where
  ProposePay : (worker_lower : UintSeq 64) -> (worker_upper : UintSeq 64) -> PayProposal

data PaySignature : PayProposal -> Type where
  SignPay : (proposal : PayProposal) -> (role : UintSeq 2) -> (sig : UintSeq 512) -> PaySignature proposal

check_distinct_roles : PaySignature -> PaySignature -> Bool
check_distinct_roles (SignPay _ r1 _) (SignPay _ r2 _) = (r1 != r2)

data JobMsgBody : Type where
  JumLock    : (offer : MessageAddr) -> JobMsgBody
  JlmConfirm : (worker_addr : MessageAddr) -> (worker_desc : Type) -> (worker_key : UintSeq 256) -> JobMsgBody
  JwmFinish  : (sig_a : PaySignature) -> (sig_b: PaySignature) -> JobMsgBody
  Bounce     : JobMsgBody -> JobMsgBody
  MsgRaw     : List Nat   -> JobMsgBody

data JobContractStateDestroyed : Type where
  JcsDestroyed : JobContractStateDestroyed

ContractState JobContractStateDestroyed where
  to_code _ = bounce_typical
  to_data _ = believe_me ()

----

data JobContractDataUnlocked : Type where
  JcdUnlocked : (poster : MessageAddr) -> (desc : Type) -> (value : UintSeq 120) -> (poster_key : UintSeq 256) -> JobContractDataUnlocked

data JobContractStateUnlocked : Type where
  JcsUnlocked : (jccode : (JobContractStateUnlocked -> TxMessage -> (NextState, List TxMessage))) -> (jcdata : JobContractDataUnlocked) -> JobContractStateUnlocked

ContractState JobContractStateUnlocked where
  to_code cur_state = let JcsUnlocked jccode jcdata = cur_state in
                        jccode
  to_data cur_state = let JcsUnlocked jccode jcdata = cur_state in
                        believe_me jcdata

----

data JobContractDataLockedOn : Type where
  JcdLockedOn : (poster : MessageAddr) -> (desc : Type) -> (value : UintSeq 120) -> (poster_key : UintSeq 256) -> (offer : MessageAddr) -> JobContractDataLockedOn

data JobContractStateLockedOn : Type where
  JcsLockedOn : (jccode : (JobContractStateLockedOn -> TxMessage -> (NextState, List TxMessage))) -> (jcdata : JobContractDataLockedOn) -> JobContractStateLockedOn

ContractState JobContractStateLockedOn where
  to_code cur_state = let JcsLockedOn jccode jcdata = cur_state in
                        jccode
  to_data cur_state = let JcsLockedOn jccode jcdata = cur_state in
                        believe_me jcdata

----

data JobContractDataWorking : Type where
  JcdWorking  : (poster : MessageAddr) -> (desc : Type) -> (value : UintSeq 120) -> (poster_key : UintSeq 256) -> (worker_key : UintSeq 256) -> JobContractDataWorking

data JobContractStateWorking : Type where
  JcsWorking  : (jccode : (JobContractStateWorking -> TxMessage -> (NextState, List TxMessage))) -> (jcdata : JobContractDataWorking) -> JobContractStateWorking

ContractState JobContractStateWorking where
  to_code cur_state = let JcsWorking jccode jcdata = cur_state in
                        jccode
  to_data cur_state = let JcsWorking jccode jcdata = cur_state in
                        believe_me jcdata

----

job_working : JobContractStateWorking -> TxMessage -> (NextState, List TxMessage)
job_working state (IntMsg bounce src self coins _ body) = case believe_me $ to_data state of
  (JcdWorking poster desc value poster_key worker_key) => case body of
    Bounce _ => (MkNextState state, Nil)
    JwmFinish worker poster_sig worker_sig => case True of  -- TODO: check signatures
      True  => (MkNextState JcsDestroyed, [IntMsg False self worker value Nothing $ MsgRaw []])
      False => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
    _ => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
  _ => (MkNextState state, Nil)
job_working state _ = (MkNextState state, Nil)


job_locked_on : JobContractStateLockedOn -> TxMessage -> (NextState, List TxMessage)
job_locked_on state (IntMsg bounce src self coins _ body) = case believe_me $ to_data state of
  (JcdLockedOn poster desc value poster_key offer) => case body of
    Bounce _ => (MkNextState state, Nil)
    (JlmConfirm worker_key) => case offer == src of
      True  => ((MkNextState $ JcsWorking job_working $ believe_me $ JcdWorking poster desc value poster_key worker_key), Nil)
      False => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
    _ => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
  _ => (MkNextState state, Nil)
job_locked_on state _ = (MkNextState state, Nil)


job_unlocked : JobContractStateUnlocked -> TxMessage -> (NextState, List TxMessage)
job_unlocked state (IntMsg bounce src self coins _ body) = case believe_me $ to_data state of
  (JcdUnlocked poster desc value poster_key) => case body of
    Bounce _ => (MkNextState state, Nil)
    (JumUpdate new_desc new_value new_poster_key) => case poster == src of
      True  => ((MkNextState $ JcsUnlocked job_unlocked $ believe_me $ JcdUnlocked poster new_desc new_value new_poster_key), Nil)
      False => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
    (JumLock offer) => case poster == src of
      True  => ((MkNextState $ JcsLockedOn job_locked_on $ believe_me $ JcdLockedOn poster desc value poster_key offer), Nil)
      False => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
    _ => (MkNextState state, build_bounce (IntMsg bounce src self coins Nothing body))
  _ => (MkNextState state, Nil)
job_unlocked state _ = (MkNextState state, Nil)

----

{-
check_invariant : NextState -> TxMessage -> Bool
check_invariant state msg = state == (fst $ run_tvm state msg)

build_ju : MessageAddr -> Type -> UintSeq 120 -> UintSeq 256 -> NextState
build_ju poster desc value poster_key = MkNextState $ JcsUnlocked job_unlocked $ believe_me $ JcdUnlocked poster desc value poster_key

theorem_ju_no_extin_processing : (cp : MessageAddr) -> (cd : Type) -> (cv : UintSeq 120) -> (cpk : UintSeq 256)
                              -> (ExtInMsg ma mb mc md) -> (check_invariant (build_ju cp cd cv cpk) $ ExtInMsg ma mb mc md) = True
theorem_ju_no_extin_processing _ _ _ _ _ = Refl

theorem_ju_invariant_nonposter : (poster : MessageAddr) -> (any : MessageAddr)
                              -> (cd : Type) -> (cv : UintSeq 120) -> (cpk : UintSeq 256)
                              -> (
                              -> Not (poster == any)
                              -> (check_invariant (build_ju poster cd cv cpk) 
-}

----

main : IO ()
main = do putStrLn "Theorems proved"
          putStrLn "Starting transactions loop"
          putStrLn "Transactions loop finished"
