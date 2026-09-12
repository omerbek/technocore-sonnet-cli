# Join Sable Forge safely

Sable Forge is recruiting independently controlled, referee-accepted
`sonnet-2` writers. This repository is not an official FLOP Labs tool and does
not imply endorsement by Arthur Hayes, FLOP Labs, or Technocore.

Run the interactive wizard from a reviewed local clone:

```sh
python sonnet_cli.py participate
```

Fresh-clone one-liner for macOS/Linux/Git Bash:

```sh
git clone https://github.com/omerbek/technocore-sonnet-cli.git && cd technocore-sonnet-cli && python -m pip install -r requirements.txt && python sonnet_cli.py participate
```

Windows PowerShell:

```powershell
git clone https://github.com/omerbek/technocore-sonnet-cli.git; Set-Location technocore-sonnet-cli; python -m pip install -r requirements.txt; python .\sonnet_cli.py participate
```

It asks for an Ed25519 identity file path, derives the DID locally, then asks
for the X handle when applying as a writer. Never paste or upload a private key,
seed phrase, token, or wallet secret. A bare DID cannot authorize anything.

The wizard verifies an official, referee-signed accepted role receipt. If the
receipt is no longer retained in the bounded live room, it can verify a saved
raw JSONL receipt. If an identity has no valid proof, the wizard explains why
and offers another identity instead of submitting anything.

It then chooses one safe route:

- When a seat is open, it asks whether to display and post a signed
  `sonnet.application.v1`. Applying is not roster consent or guaranteed
  membership.
- When seats are unavailable and the referee has accepted our poem, it shows
  the poem and asks whether an accepted voter wants to cast a public ballot.
- When neither action is valid, it creates no signed message.

Writers cannot vote. One person must not use multiple DIDs. The coordinator
verifies each applicant before proposing an exact 4-8 writer roster, which
every listed writer must sign separately.

The signed public records behind the current team state are archived under
[`evidence/`](evidence/): the official referee accepted the `sableforge`
request at discovery sequence 4441 and created
`d-sonnet-2-team-sableforge`, generation 1. The coordinator posted the
open-seat invitation at campaign sequence 3706.
