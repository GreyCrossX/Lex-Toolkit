#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import tiktoken

from services.data_pipeline.embed_chunks import (
    ChunkFile,
    ChunkRecord,
    iter_chunk_files,
    iter_chunk_records,
)


def _load_encoding(name: str) -> tiktoken.Encoding:
    try:
        return tiktoken.get_encoding(name)
    except Exception as exc:  # pragma: no cover - defensive/offline handling
        raise RuntimeError(
            f"Failed to load tiktoken encoding '{name}'. "
            "Allow network access or pre-cache the encoding files."
        ) from exc


def get_encoding(model: str) -> tiktoken.Encoding:
    """
    Resolve a tiktoken encoding for the given model name.
    Falls back to cl100k_base when the model is unknown or unavailable.
    """
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return _load_encoding("cl100k_base")
    except Exception:  # pragma: no cover - defensive/offline handling
        return _load_encoding("cl100k_base")


def tokenize_text(text: str, encoding: tiktoken.Encoding) -> List[int]:
    """Encode text into token ids using the provided encoding."""
    normalized = text if isinstance(text, str) else str(text or "")
    return encoding.encode_ordinary(normalized)


def annotate_record(
    record: ChunkRecord,
    encoding: tiktoken.Encoding,
    *,
    tokenizer_model: str,
    include_token_ids: bool = False,
    tokens: Optional[List[int]] = None,
) -> Dict[str, object]:
    token_ids = (
        tokens
        if tokens is not None
        else tokenize_text(record.get("content") or "", encoding)
    )
    annotated = dict(record)
    annotated["token_count"] = len(token_ids)
    annotated["tokenizer_model"] = tokenizer_model
    if include_token_ids:
        annotated["token_ids"] = token_ids
    return annotated


def validate_round_trip(
    text: str, token_ids: Sequence[int], encoding: tiktoken.Encoding
) -> None:
    """
    Ensure tokens decode back to the original string; raises ValueError on mismatch.
    Useful for catching boundary/UTF edge cases.
    """
    decoded = encoding.decode(token_ids)
    if decoded != text:
        raise ValueError(
            "Token decode mismatch: original and decoded text differ "
            "(potential boundary or encoding issue)."
        )


def tokenize_file(
    chunk_file: ChunkFile,
    out_dir: Path,
    encoding: tiktoken.Encoding,
    *,
    tokenizer_model: str,
    include_token_ids: bool,
    save_token_ids_npy: bool,
    validate_decode: bool,
    max_chunks: Optional[int],
    processed_so_far: int,
    batch_size: int,
    num_threads: int,
) -> int:
    """Tokenize a single chunk JSONL file and write annotated records."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{chunk_file.doc_id}_tokens.jsonl"

    processed = 0
    limit = None if max_chunks is None else max_chunks - processed_so_far

    npy_chunk_ids: List[str] = []
    npy_lengths: List[int] = []
    npy_flat_tokens: List[int] = []

    with out_path.open("w", encoding="utf-8") as out_f:
        buffer: List[ChunkRecord] = []

        def flush_buffer() -> None:
            nonlocal processed, buffer
            if not buffer:
                return
            texts = [(rec.get("content") or "") for rec in buffer]
            token_batches = encoding.encode_ordinary_batch(
                texts,
                num_threads=num_threads,
            )
            for rec, token_ids in zip(buffer, token_batches):
                text = rec.get("content") or ""
                if validate_decode:
                    validate_round_trip(text, token_ids, encoding)
                annotated = annotate_record(
                    rec,
                    encoding,
                    tokenizer_model=tokenizer_model,
                    include_token_ids=include_token_ids,
                    tokens=token_ids,
                )
                out_f.write(json.dumps(annotated, ensure_ascii=False) + "\n")
                if include_token_ids and save_token_ids_npy:
                    npy_chunk_ids.append(str(rec.get("chunk_id", "")))
                    npy_lengths.append(len(token_ids))
                    npy_flat_tokens.extend(token_ids)
                processed += 1
            buffer = []

        for record in iter_chunk_records(chunk_file.path):
            if limit is not None and processed >= limit:
                break
            buffer.append(record)
            if len(buffer) >= batch_size or (
                limit is not None and processed + len(buffer) >= limit
            ):
                flush_buffer()
        flush_buffer()

    if include_token_ids and save_token_ids_npy and npy_chunk_ids:
        token_array = np.array(npy_flat_tokens, dtype=np.uint32)
        lengths_array = np.array(npy_lengths, dtype=np.int32)
        chunk_ids_array = np.array(npy_chunk_ids, dtype=object)
        np.savez(
            out_path.with_suffix(".npz"),
            chunk_ids=chunk_ids_array,
            lengths=lengths_array,
            tokens=token_array,
        )

    return processed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tokenize legal chunks with tiktoken for OpenAI models."
    )
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/chunks"),
        help="Directory containing chunk JSONL files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/tokenized_chunks"),
        help="Where to write tokenized JSONL files.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model name used to resolve the tokenizer (tiktoken).",
    )
    parser.add_argument(
        "--jurisdiction",
        action="append",
        help="Optional jurisdiction filter matching chunk subdirectories.",
    )
    parser.add_argument(
        "--doc-id",
        action="append",
        help="Optional doc id filter (filename prefix before _chunks.jsonl).",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Optional limit on number of chunks to tokenize.",
    )
    parser.add_argument(
        "--include-token-ids",
        action="store_true",
        help="Include raw token ids in the output (may increase file size).",
    )
    parser.add_argument(
        "--save-token-ids-npy",
        action="store_true",
        help="If including token ids, also write a compact .npz sidecar (chunk_ids, lengths, tokens).",
    )
    parser.add_argument(
        "--validate-decode",
        action="store_true",
        help="Validate each chunk decodes back to its original text (slower; use for debugging).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="How many chunks to tokenize per batch.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Threads to use for tiktoken batch encoding.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.chunks_dir.exists():
        raise FileNotFoundError(f"Chunks directory not found: {args.chunks_dir}")

    if args.save_token_ids_npy and not args.include_token_ids:
        raise ValueError("--save-token-ids-npy requires --include-token-ids")

    encoding = get_encoding(args.model)
    processed = 0

    for chunk_file in iter_chunk_files(
        args.chunks_dir, jurisdictions=args.jurisdiction, doc_ids=args.doc_id
    ):
        out_dir = args.output_dir / chunk_file.jurisdiction
        processed_in_file = tokenize_file(
            chunk_file,
            out_dir,
            encoding,
            tokenizer_model=args.model,
            include_token_ids=args.include_token_ids,
            save_token_ids_npy=args.save_token_ids_npy,
            validate_decode=args.validate_decode,
            max_chunks=args.max_chunks,
            processed_so_far=processed,
            batch_size=args.batch_size,
            num_threads=args.threads,
        )
        processed += processed_in_file
        if args.max_chunks is not None and processed >= args.max_chunks:
            break

    print(
        f"[DONE] Tokenized {processed} chunk(s) "
        f"with tokenizer model={args.model} into {args.output_dir}"
    )


if __name__ == "__main__":
    main()
