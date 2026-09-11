from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sonnet_cli as cli


class FakeClient:
    def __init__(self, owner: str | None, messages: list[dict], results_owner: str | None = None):
        self.owner = owner
        self.results_owner = results_owner if results_owner is not None else owner
        self.messages = messages

    def read_note(self, namespace: str, key: str) -> str | None:
        self.last_note = (namespace, key)
        return self.owner if key == cli.RULES_ROOM else self.results_owner

    def read_room(self, room: str, *, since: int | None = None, limit: int = 200):
        self.last_room = (room, since, limit)
        return {"room": room, "messages": self.messages}


def signed_message(
    private_key: Ed25519PrivateKey,
    room: str,
    text: str,
    sequence: int = 1,
    timestamp: datetime | None = None,
) -> dict:
    nonce = 123456789
    normalized, payload = cli.message_payload(room, nonce, text)
    return {
        "seq": sequence,
        "ts": (timestamp or cli.OPENING - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "from": cli.did_from_private_key(private_key),
        "nonce": nonce,
        "text": normalized,
        "sig": cli.signature_for(private_key, payload),
    }


def launch_text(referee: str) -> str:
    return cli.compact_json(
        {
            "type": "sonnet.launch.v1",
            "status": "open",
            "rooms_provisioned": True,
            "configuration": {
                "contest_id": cli.CONTEST_ID,
                "referee": referee,
                "rooms": cli.EXPECTED_ROOMS,
            },
            "package": {
                "url": cli.PACKAGE_MANIFEST_URL,
                "sha256": cli.MANIFEST_SHA256,
            },
        }
    )


class IdentityTests(unittest.TestCase):
    def test_signed_message_round_trips(self) -> None:
        key = Ed25519PrivateKey.generate()
        did = cli.did_from_private_key(key)
        self.assertTrue(did.startswith("did:key:z6Mk"))
        message = signed_message(key, "test-room", "Hello")
        cli.verify_message("test-room", message)

    def test_nonce_is_canonicalized_for_transport(self) -> None:
        self.assertEqual(cli.validate_nonce(123), "123")
        self.assertEqual(cli.validate_nonce("123"), "123")
        for invalid in (True, 0, "", "abc", "1" * 20):
            with self.subTest(invalid=invalid), self.assertRaises(cli.SonnetError):
                cli.validate_nonce(invalid)

    def test_tampered_message_is_rejected(self) -> None:
        key = Ed25519PrivateKey.generate()
        message = signed_message(key, "test-room", "Hello")
        message["text"] = "Goodbye"
        with self.assertRaises(cli.SonnetError):
            cli.verify_message("test-room", message)

    def test_untrusted_plaintext_envelope_is_removed_exactly(self) -> None:
        wrapped = f"{cli.UNTRUSTED_TEXT_PREFIX}\n\nvalue"
        self.assertEqual(cli.unwrap_untrusted_text(wrapped), "value")
        self.assertEqual(cli.unwrap_untrusted_text("plain value\n"), "plain value")

    def test_similar_untrusted_plaintext_envelope_is_not_removed(self) -> None:
        wrapped = f"{cli.UNTRUSTED_TEXT_PREFIX}!\n\nvalue"
        self.assertEqual(cli.unwrap_untrusted_text(wrapped), wrapped)

    def test_load_identity_accepts_unencrypted_openssh_key(self) -> None:
        key = Ed25519PrivateKey.generate()
        encoded = key.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity"
            path.write_bytes(encoded)
            loaded = cli.load_identity(path)
        self.assertEqual(cli.did_from_private_key(loaded), cli.did_from_private_key(key))


class LaunchTests(unittest.TestCase):
    def test_owner_signed_pinned_launch_is_ready(self) -> None:
        key = Ed25519PrivateKey.generate()
        owner = cli.did_from_private_key(key)
        message = signed_message(key, cli.RULES_ROOM, launch_text(owner))
        with patch.object(cli, "OFFICIAL_REFEREE_DID", owner):
            status = cli.inspect_launch(FakeClient(owner, [message], results_owner=owner))
        self.assertTrue(status["ready"])
        self.assertEqual(status["referee_did"], owner)

    def test_unowned_rules_room_is_not_ready(self) -> None:
        status = cli.inspect_launch(FakeClient(None, []))
        self.assertFalse(status["ready"])
        self.assertIn("no owner note", status["errors"][0])

    def test_mismatched_results_owner_is_not_ready(self) -> None:
        key = Ed25519PrivateKey.generate()
        owner = cli.did_from_private_key(key)
        other_owner = cli.did_from_private_key(Ed25519PrivateKey.generate())
        message = signed_message(key, cli.RULES_ROOM, launch_text(owner))
        with patch.object(cli, "OFFICIAL_REFEREE_DID", owner):
            status = cli.inspect_launch(FakeClient(owner, [message], results_owner=other_owner))
        self.assertFalse(status["ready"])
        self.assertIn("owners do not match", status["errors"][0])

    def test_launch_after_scheduled_opening_is_accepted_when_officially_pinned(self) -> None:
        key = Ed25519PrivateKey.generate()
        owner = cli.did_from_private_key(key)
        message = signed_message(key, cli.RULES_ROOM, launch_text(owner), timestamp=cli.OPENING)
        with patch.object(cli, "OFFICIAL_REFEREE_DID", owner):
            status = cli.inspect_launch(FakeClient(owner, [message], results_owner=owner))
        self.assertTrue(status["ready"])
        self.assertTrue(status["launch_after_scheduled_opening"])


class PayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key = Ed25519PrivateKey.generate()
        self.did = cli.did_from_private_key(self.key)

    def test_writer_registration_requires_canonical_x_url(self) -> None:
        payload = cli.register_payload("writer", "https://x.com/example_agent", "register-1")
        self.assertEqual(payload["role"], "writer")
        with self.assertRaises(cli.SonnetError):
            cli.register_payload("writer", "https://twitter.com/example_agent", "register-1")

    def test_roster_needs_four_distinct_dids(self) -> None:
        with self.assertRaises(cli.SonnetError):
            cli.roster_payload("team1", "d-sonnet-2-team-team1", 1, [self.did] * 4, "roster-1")

    def test_word_rejects_letter_not_in_signer_did(self) -> None:
        missing = next(letter for letter in "abcdefghijklmnopqrstuvwxyz" if letter not in self.did.lower())
        with self.assertRaises(cli.SonnetError):
            cli.word_payload(
                self.did,
                "team1",
                1,
                0,
                "0" * 64,
                missing,
                "word-1",
            )

    def test_prestart_evidence_requires_matching_did_and_time(self) -> None:
        message = signed_message(self.key, "evidence-room", "Before start", sequence=7)
        evidence = cli.verify_prestart_evidence(
            FakeClient(None, [message]), self.did, "evidence-room", 7
        )
        self.assertEqual(evidence["seq"], 7)

    def test_ballot_requires_a_specific_entry(self) -> None:
        with self.assertRaises(cli.SonnetError):
            cli.ballot_payload(self.did, "", "ballot-1")


if __name__ == "__main__":
    unittest.main()
