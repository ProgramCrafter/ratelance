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
- Vote for us in Hack-a-TONx: https://dorahacks.io/buidl/4227
- Propose something, report a bug, etc: [issues](https://github.com/ProgramCrafter/ratelance/issues)

## Install

```
$ git clone https://github.com/ProgramCrafter/ratelance.git
$ pip3 install tonsdk pynacl requests
$ cd ratelance/cli
$ python3 main.py
```

## Current state

- `contracts` :white_check_mark:
  - platform contracts with unit tests
- `cli`
  - [x] Getting information about jobs, posting and revoking
  - [x] Applying for jobs, revoking offers
  - [ ] Verifying for job/offer existence and validity
  - [x] Listing offers, delegating job to someone
  - [ ] Encrypted communication channel on top of job contract
  - [x] Negotiating payments
  - [x] Working with keyring
  - [ ] Integration with system keys storage/using password for keyring encryption
- `freelance-highlevel.idr`
  - [x] High-level contracts representation
  - [ ] Storing contracts' balances
  - [x] Transaction loop implementation
  - [ ] Proof that transaction loop terminates (based on balances)
  - [x] Freelance job contract types
  - [x] Freelance job contract code
  - [ ] Freelance worker contract types
  - [ ] Freelance worker contract code
  - [ ] Job contract theorems
  - [ ] Job contract theorems' proofs
  - [ ] Worker (offer) contract theorems
  - [ ] Worker (offer) contract theorems' proofs

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
 - worker+TON validators &ndash; heavy disagreement between poster and worker, so that Ratelance cannot be a referee
 - Ratelance+TON         &ndash; order is deemed so inacceptible by TON that even voting is conducted
---
11. Single-party-signed messages go to job or other pre-established address as analytic messages with minimal value.
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
- `7.`  - Insufficient money to lock the contract. Taking +0.1 TON (total 0.8).  
        - Contract does not exist, message bounces.
- `6.`  Insufficient funds to lock the contract. Taking +0.2 TON (total 1.0).
- `5.`  &nbsp;&ndash;
- `4.`  &nbsp;&ndash;
- `3.`  &nbsp;&ndash;
- `2.`  &nbsp;&ndash;
- `1.`  &nbsp;&ndash;
