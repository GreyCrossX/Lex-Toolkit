import unittest
from pathlib import Path

from services.data_pipeline.tokenize_chunks import (
    annotate_record,
    get_encoding,
    validate_round_trip,
    tokenize_text,
)
import numpy as np


class TokenizeChunksTests(unittest.TestCase):
    def test_tokenize_text_round_trips(self) -> None:
        try:
            encoding = get_encoding("gpt-4o-mini")
        except RuntimeError as exc:
            self.skipTest(f"Tokenizer unavailable offline: {exc}")
        text = "Hola mundo. Artículo 1: Obligaciones."
        tokens = tokenize_text(text, encoding)
        self.assertGreater(len(tokens), 3)
        self.assertEqual(encoding.decode(tokens), text)

    def test_falls_back_for_unknown_model(self) -> None:
        try:
            encoding = get_encoding("unknown-model")
        except RuntimeError as exc:
            self.skipTest(f"Tokenizer unavailable offline: {exc}")
        tokens = tokenize_text("test", encoding)
        self.assertEqual(encoding.decode(tokens), "test")

    def test_annotate_record_adds_count(self) -> None:
        try:
            encoding = get_encoding("gpt-4o-mini")
        except RuntimeError as exc:
            self.skipTest(f"Tokenizer unavailable offline: {exc}")
        record = {
            "chunk_id": "doc:art1:fraclead:p1:c0",
            "doc_id": "doc",
            "content": "Hola mundo",
        }
        annotated = annotate_record(
            record,
            encoding,
            tokenizer_model="gpt-4o-mini",
            include_token_ids=False,
        )
        self.assertIn("token_count", annotated)
        self.assertEqual(annotated["tokenizer_model"], "gpt-4o-mini")
        self.assertNotIn("token_ids", annotated)
        self.assertGreater(annotated["token_count"], 0)

    def test_numpy_sidecar_shapes(self) -> None:
        # Quick structural check for token npy packing
        tokens = [1, 2, 3, 4]
        lengths = [len(tokens)]
        chunk_ids = ["doc:art1:fraclead:p1:c0"]
        token_array = np.array(tokens, dtype=np.uint32)
        lengths_array = np.array(lengths, dtype=np.int32)
        chunk_ids_array = np.array(chunk_ids, dtype=object)
        # Simulate save/load round-trip in-memory
        npz_path = Path("/tmp/token_test_sidecar.npz")
        np.savez(npz_path, chunk_ids=chunk_ids_array, lengths=lengths_array, tokens=token_array)
        loaded = np.load(npz_path, allow_pickle=True)
        self.assertTrue((loaded["tokens"] == token_array).all())
        self.assertTrue((loaded["lengths"] == lengths_array).all())
        self.assertEqual(list(loaded["chunk_ids"]), chunk_ids)
        npz_path.unlink(missing_ok=True)

    def test_validate_round_trip(self) -> None:
        try:
            encoding = get_encoding("gpt-4o-mini")
        except RuntimeError as exc:
            self.skipTest(f"Tokenizer unavailable offline: {exc}")
        text = "Hola mundo"
        tokens = tokenize_text(text, encoding)
        # Should not raise
        validate_round_trip(text, tokens, encoding)
        # Introduce mismatch to force failure
        with self.assertRaises(ValueError):
            validate_round_trip(text, tokens[:-1], encoding)


if __name__ == "__main__":
    unittest.main()
