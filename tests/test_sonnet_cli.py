from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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


class IdentityTests(unittest.TestCase):
    def test_signed_message_round_trips(self) -> None:
        key = Ed25519PrivateKey.generate()
        did = cli.did_from_private_key(key)
        self.assertTrue(did.startswith("did:key:z6Mk"))
        message = signed_message(key, "test-room", "Hello")
        cli.verify_message("test-room", message)

    def test_tampered_message_is_rejected(self) -> None:
        key = Ed25519PrivateKey.generate()
        message = signed_message(key, "test-room", "Hello")
        message["text"] = "Goodbye"
        with self.assertRaises(cli.SonnetError):
            cli.verify_message("test-room", message)


class LaunchTests(unittest.TestCase):
    def test_owner_signed_pinned_launch_is_ready(self) -> None:
        key = Ed25519PrivateKey.generate()
        launch_text = (
            f"launch {cli.CONTEST_ID} package {cli.RULES_COMMIT} "
            f"manifest {cli.MANIFEST_SHA256}"
        )
        message = signed_message(key, cli.RULES_ROOM, launch_text)
        owner = cli.did_from_private_key(key)
        status = cli.inspect_launch(FakeClient(owner, [message], results_owner=owner))
        self.assertTrue(status["ready"])
        self.assertEqual(status["referee_did"], cli.did_from_private_key(key))

    def test_unowned_rules_room_is_not_ready(self) -> None:
        status = cli.inspect_launch(FakeClient(None, []))
        self.assertFalse(status["ready"])
        self.assertIn("no owner note", status["errors"][0])

    def test_mismatched_results_owner_is_not_ready(self) -> None:
        key = Ed25519PrivateKey.generate()
        other_owner = cli.did_from_private_key(Ed25519PrivateKey.generate())
        text = f"{cli.CONTEST_ID} {cli.RULES_COMMIT} {cli.MANIFEST_SHA256}"
        message = signed_message(key, cli.RULES_ROOM, text)
        status = cli.inspect_launch(
            FakeClient(cli.did_from_private_key(key), [message], results_owner=other_owner)
        )
        self.assertFalse(status["ready"])
        self.assertIn("owners do not match", status["errors"][0])

    def test_late_launch_is_not_ready(self) -> None:
        key = Ed25519PrivateKey.generate()
        text = f"{cli.CONTEST_ID} {cli.RULES_COMMIT} {cli.MANIFEST_SHA256}"
        message = signed_message(key, cli.RULES_ROOM, text, timestamp=cli.OPENING)
        status = cli.inspect_launch(FakeClient(cli.did_from_private_key(key), [message]))
        self.assertFalse(status["ready"])
        self.assertIn("before opening", status["errors"][0])


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
            cli.roster_payload("team1", "d-sonnet-1-team-team1", 1, [self.did] * 4, "roster-1")

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
