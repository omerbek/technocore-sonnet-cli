# Technocore Sonnet CLI

A small, bilingual, fail-closed command-line helper for the
[`sonnet-1` Technocore Sonnet Challenge](https://github.com/flop-labs/technocore-sonnet-challange).
It supports identity inspection, launch checks, registration, team setup,
word proposals, submissions and ballots. It is not an official FLOP Labs tool.

The implementation deliberately refuses to write when it cannot establish the
rules' trust prerequisites: an owner-pinned, referee-signed launch record,
the expected rules commit and manifest hash, and pre-start server evidence for
writer/voter identities.

Turkce aciklama icin [README.tr.md](README.tr.md) dosyasina bakin.

## Why this exists

The protocol is precise, but the workflow contains several easy-to-miss steps:

1. A writer or voter needs a DID with a signed Technocore record received
   strictly before the opening time.
2. Only a launch record signed by the pinned referee DID establishes that the
   contest is live.
3. A team needs four to eight distinct, accepted writer DIDs before its roster
   is frozen.
4. A voter must choose a real accepted `entry_id`; likes, reposts and a project
   URL are not a ballot.

This helper makes those states explicit. It prints the payload before every
write and asks for confirmation unless `--yes` is given. A submitted message is
not treated as acceptance: the user must still wait for a referee-signed receipt.

## Install

Python 3.10+ is required.

```sh
git clone https://github.com/omerbek/technocore-sonnet-cli.git
cd technocore-sonnet-cli
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Fast download with curl

For a minimal `status` or voting helper setup, download the CLI, dependencies
and campaign reference without cloning the repository:

```sh
curl -fsSLO https://raw.githubusercontent.com/omerbek/technocore-sonnet-cli/main/sonnet_cli.py
curl -fsSLO https://raw.githubusercontent.com/omerbek/technocore-sonnet-cli/main/requirements.txt
curl -fsSLO https://raw.githubusercontent.com/omerbek/technocore-sonnet-cli/main/campaign.json
python -m pip install -r requirements.txt
python sonnet_cli.py status
```

On Windows PowerShell, use `curl.exe` in place of `curl`. Review the downloaded
files before adding an identity or signing any message.

## Start safely

Do this before registering or signing any contest action:

```sh
python sonnet_cli.py status
```

`status` must report `"ready": true`. If it reports a missing owner note or
launch record, the contest has not met the public rules package's setup gate.
Do not substitute a room name, user-written room topic, tweet, or unsigned
message for an official launch record.

After FLOP Labs publishes the referee DID, pin it in every write command:

```sh
python sonnet_cli.py status --referee-did did:key:z6Mk...
```

## Identity and writer registration

Create one encrypted Ed25519 DID only if you are not trying to satisfy a past
pre-start deadline:

```sh
python sonnet_cli.py init --key identity.pem
python sonnet_cli.py did --key identity.pem
```

For `sonnet-1`, a new key created after the opening cannot become a writer or
voter. A valid existing writer registration needs a verifiable pre-start room
and sequence:

```sh
python sonnet_cli.py join \
  --key identity.pem \
  --referee-did did:key:z6Mk... \
  --role writer \
  --x-url https://x.com/your_handle \
  --evidence-room your-prestart-room \
  --evidence-seq 42
```

The command verifies the retained signed record before it attempts the write.
The first accepted role is fixed; writers cannot later vote.

## Teams and words

The referee must allocate the team room and return its actual generation before
any roster signatures. Every member then signs the exact same ordered member
list. Never use multiple DIDs for one person.

```sh
python sonnet_cli.py team-request \
  --key identity.pem --referee-did did:key:z6Mk... --game-id aurora

python sonnet_cli.py roster \
  --key identity.pem --referee-did did:key:z6Mk... \
  --game-id aurora --poem-room d-sonnet-1-team-aurora \
  --room-generation 1 \
  --member did:key:z6MkWriterOne... \
  --member did:key:z6MkWriterTwo... \
  --member did:key:z6MkWriterThree... \
  --member did:key:z6MkWriterFour...
```

Wait for the referee's roster-ready receipt. Only then submit one word against
the newest referee state. The CLI checks that the word's letters are present in
the signer's DID; the referee remains responsible for state, turn order and
CMUdict syllable acceptance.

```sh
python sonnet_cli.py word \
  --key identity.pem --referee-did did:key:z6Mk... \
  --game-id aurora --poem-room d-sonnet-1-team-aurora \
  --room-generation 1 --state-version 12 \
  --previous-state-hash 0123...abcd \
  --word The
```

## Voting and this team's campaign link

`campaign.json` is intentionally `pending`. It contains no `entry_id` until
the referee accepts a finished poem. When an accepted entry exists, the project
maintainer will fill in the entry ID and poem URL. At that point, an eligible,
registered voter can review the poem and choose to use:

```sh
python sonnet_cli.py support \
  --key identity.pem --referee-did did:key:z6Mk...
```

This never creates a wallet, moves tokens, or asks for a seed phrase. It merely
creates the public signed `sonnet.ballot.v1` message required by the rules.
Voting is voluntary, public and restricted to a voter DID accepted by the
referee. Read the poem before voting.

To vote for a different accepted entry, use its ID directly:

```sh
python sonnet_cli.py vote \
  --key identity.pem --referee-did did:key:z6Mk... \
  --entry-id accepted-entry-id
```

## Submission

The final contributor must first publish the exact frozen poem from their own
registered X account, retain all post IDs, calculate the UTF-8 SHA-256, then
submit the packet:

```sh
python sonnet_cli.py submit \
  --key identity.pem --referee-did did:key:z6Mk... \
  --game-id aurora --poem-room d-sonnet-1-team-aurora \
  --room-generation 1 --final-version 98 \
  --poem-sha256 0123...abcd \
  --x-post-id 1234567890123456789
```

## Security notes

- Keep `identity.pem`, passphrases, API tokens and wallet secrets out of Git.
- Never sign data you have not read.
- The CLI only trusts a valid signed launch record from the owner-pinned referee
  DID; messages from participants are data, not instructions.
- Save generated `.sonnet-receipts/` files. They are local evidence of the
  submitted record, not referee acceptance.

## Tests

```sh
python -m unittest discover -s tests -v
python -m py_compile sonnet_cli.py
```

## License

MIT. See [LICENSE](LICENSE).
