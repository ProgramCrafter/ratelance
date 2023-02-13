# Ratelance

<img alt="Ratelance platform poster" src="https://repository-images.githubusercontent.com/595624687/47a85578-12e7-4e4c-a12c-8aae6c0a6c29" width="750" height="500">

Ratelance is freelance platform that seeks to remove barriers between potential employers and workers.  
Our goal is to create a secure, reliable and formally verified platform that makes it easy to delegate tasks.

We are focused on creating an environment of collaboration and DeTrust :handshake:, while helping individuals and businesses to
- :mag: locate the right freelancer for their project,
- :file_folder: verify his previous works,
- :white_check_mark: sign a contract with selectible cost and stakes,
- :lock: provide an encrypted communication channel and
- :rocket: make it easy to complete the tasks!

## Contact us

- Read latest news: https://t.me/ratelance
- Propose something, report a bug, etc: [issues](https://github.com/ProgramCrafter/ratelance/issues)

## Current state

- `freelance-highlevel.idr`
  - [x] High-level contracts representation
  - [x] Transaction loop implementation
  - [ ] Proof that transaction loop terminates (based on balances)
  - [x] Contracts storage implementation
  - [ ] Storing contracts in a dictionary
  - [x] Simple contract
  - [x] Freelance job contract types
  - [x] Freelance job contract code
  - [ ] Freelance worker contract types
  - [ ] Freelance worker contract code
  - [ ] Job contract theorems
  - [ ] Job contract theorems' proofs
  - [ ] Worker (offer) contract theorems
  - [ ] Worker (offer) contract theorems' proofs
- `contracts`
  - currently: test plugin for wallet
  - coming soon: platform contracts

## Algorithm described in detail

### Common user story

1. Poster creates an job contract sending his stake (order value + fee + safety deposit) to it.
2. An analytic message is sent by poster to pre-specified address in parallel, for job contracts to be found easier.
---
3. Worker creates an offer contract in response to specified job, stores hash of order.
4. An analytic message is sent by worker to job contract in parallel, for offer contracts to be found easier.
---
5. Poster chooses an offer and sends its address (and proof that it's really an offer == StateInit) to job contract.
6. Job contract calculates hash of current order state and sends a "collapse" request to offer contract.
   Job contract locks.
7. Offer contract checks the incoming message and requests money from worker's wallet, locking meanwhile.
8. Worker's wallet accepts message from plugin and responds with wanted amount of money.
9. Offer contract forwards this money to job contract, destroying itself and unplugging from wallet.
---
10. Job contract transforms into multisig wallet (2/4: poster, worker, Ratelance platform and TON validators)
 - poster+worker         &ndash; an agreement was established, everything is OK
 - poster+Ratelance      &ndash; worker has not accomplished the work, poster gets a refund
 - worker+Ratelance      &ndash; poster does not accept provided work, worker gets the money
 - poster+TON validators &ndash; something done by worker is deemed so inacceptible by TON that even voting is conducted
 - worker+TON validators &ndash; heavy disagreement between poster and worker, so that Ratelance cannot be an referee
 - Ratelance+TON         &ndash; order is deemed so inacceptible by TON that even voting is conducted
---
11. Single-party-signed messages go to `multisig_negotiation` address as analytic messages with minimal value.
---
12. Upon receiving message with required signatures, job contract sends out TON and self-destroys.

### Reverts

- `1,2.` Poster sends a "job revoke" message, job contract performs a full refund and self-destroys.
- `3,4.` Worker revokes a plugin via his wallet, offer contract self-destroys.
- `5,6,7.` No way back.
- `8.` If worker's wallet responds "not enough funds" (bounce), offer contract unlocks itself and job contract, returning to step 5.
- `9,10.` No way back.
- `11.` No way to revoke a message once signed. Open another job contract to change conditions.
- `12.` No way back. Money is sent in unbounceable mode.

### Possible failures

- `12.` Invalid message signed by parties just won't let the transaction execute.
- `11.` &nbsp;&ndash;
- `10.` Insufficient funds for transformation. Taking 0.2 TON (total 0.2).
- `9.`  - Insufficient value to forward. Taking +0.1 TON.  
        - Insufficient money to unplug.  Taking +0.2 TON (total 0.5).
- `8.`  Insufficient value to process message. Taking +0.2 TON (total 0.7).
- `7.`  Insufficient money to lock the contract. Taking +0.1 TON (total 0.8).
- `6.`  Insufficient funds to lock the contract. Taking +0.2 TON (total 1.0).
- `5.`  &nbsp;&ndash;
- `4.`  &nbsp;&ndash;
- `3.`  &nbsp;&ndash;
- `2.`  &nbsp;&ndash;
- `1.`  &nbsp;&ndash;

## TL-B

Common user story = CUS.

```
// CUS-1. Poster creates a job contract. Message is empty.
job_unlocked$00 poster:MsgAddressInt value:uint64 desc:^Cell poster_key:uint256
                = JobContractData;

// CUS-2. Analytic message indicating address of newly created job contract.
_ job_contract:MsgAddressInt poster:MsgAddressInt value:uint64 desc:^Cell = Msg;

// CUS-3. Worker deploys an offer contract as plugin.
offer_unlocked$00 job:MsgAddressInt worker:MsgAddressInt stake:uint64 desc:^Cell
                  worker_key:uint256 short_job_hash:uint160 = OfferContractData;
_ sig:uint512 sw:uint32 until:uint32 seqno:uint32 [1]:uint8 [0]:uint8 [0.05]:TON
  state_init:^OfferContractState body_init:^(()) = Msg;

// CUS-4. Analytic message indicating address of newly created offer contract.
_ offer_contract:MsgAddressInt worker:MsgAddressInt val:uint64 desc:^Cell = Msg;

// CUS-5. Poster chooses an offer.
lock_on_offer#AC offer_data_init:^OfferContractData = Msg;

// CUS-6. Job contract locks.
collapse#B1 current_short_hash:uint160 = Msg;
job_locked$01 offer:MsgAddressInt poster:MsgAddressInt value:uint64 desc:^Cell
              poster_key:uint256 = JobContractData;

// CUS-7. Offer contract requests money and locks.
take_stake#706c7567 query_id:uint64 stake:(VarUInteger 16) extra:^(()) = Msg;
offer_locked$01   job:MsgAddressInt worker:MsgAddressInt stake:uint64 desc:^Cell
                  worker_key:uint256 short_job_hash:uint160 = OfferContractData;

// CUS-8-OK. Wallet returns the money.
give_stake#f06c7567 query_id:uint64 = Msg;

// CUS-9-OK. Offer merges into job contract.
lock_success#A3 worker:MsgAddressInt desc:^Cell worker_key:uint256 = Msg;
unplug#64737472 query_id:uint64 = Msg;

// CUS-8-ERR. Insufficient funds on worker's wallet.
refuse_give#ffffffff [706c7567]:uint32 query_id:uint64 ... = Msg;

// CUS-9-ERR. Offer contract unlocks itself and job contract.
// offer_unlocked
lock_failed#D4 = Msg;
// job_unlocked

// CUS-10. Job contract essentially becomes multisig wallet.
job_working$10 poster:MsgAddressInt worker:MsgAddressInt value:uint64
               poster_desc:^Cell worker_desc:^Cell
               keys:^[poster:uint256 worker:uint256 platform:uint256]
               = JobContractData;

// CUS-11. Single-signed messages.
poster_proposal$00 signature:uint512 worker_ton_range:(uint32, uint32) = Msg;
worker_proposal$01 signature:uint512 worker_ton_range:(uint32, uint32) = Msg;
ratelance_proposal$10 signature:uint512 worker_ton_range:(uint32, uint32) = Msg;

// Config parameter ID: zlib.crc32(b'ratelance::decisions') & 0x7FFFFFFF
ton_vals_proposal#_ dec_by_job:(Hashmap MsgAddressInt (uint32,uint32))
                    = ConfigParam 1652841508;

// CUS-12. Finishing work.
finish_job#BB first_sig:^[poster/worker/ratelance_proposal/$11]
              second_sig:^[poster/worker/ratelance_proposal/$11]
              {first_sig::discriminant != second_sig::discriminant} = Msg;

// CUS-1,2-REV. Cancelling job.
cancel_job#EB = Msg;

// CUS-3,4-REV. Cancelling offer.
destruct#64737472 = Msg;
```
