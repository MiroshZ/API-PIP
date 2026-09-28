"""CSV -> OpenAI LLM -> validated JSON pipeline for review classification."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict, Field


DEFAULT_MODEL = "gpt-6-astra"


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class ReviewAnalysis(BaseModel):
    """Schema for one item returned by the LLM."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="The unchanged review ID from the input")
    sentiment: Literal["positive", "negative", "neutral"]
    topic: Literal[
        "product_quality",
        "delivery",
        "customer_service",
        "price",
        "usability",
        "other",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewAnalysisBatch(BaseModel):
    """Strict structured-output schema sent to the OpenAI SDK."""

    model_config = ConfigDict(extra="forbid")

    results: list[ReviewAnalysis]


def load_reviews(path: Path) -> list[Review]:
    """Read and validate a UTF-8 CSV containing id and text columns."""

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not {"id", "text"}.issubset(reader.fieldnames):
            raise ValueError("CSV must contain the columns 'id' and 'text'")

        reviews: list[Review] = []
        seen_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            review_id = (row.get("id") or "").strip()
            text = (row.get("text") or "").strip()
            if not review_id or not text:
                raise ValueError(f"Row {row_number}: id and text must not be empty")
            if review_id in seen_ids:
                raise ValueError(f"Row {row_number}: duplicate id '{review_id}'")
            seen_ids.add(review_id)
            reviews.append(Review(id=review_id, text=text))

    if not reviews:
        raise ValueError("CSV contains no reviews")
    return reviews


def _chunks(items: list[Review], size: int) -> list[list[Review]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def analyze_reviews(
    client: OpenAI,
    reviews: list[Review],
    model: str,
    batch_size: int,
) -> list[ReviewAnalysis]:
    """Send review batches to the LLM and validate its structured response."""

    analyses: list[ReviewAnalysis] = []
    for batch_number, batch in enumerate(_chunks(reviews, batch_size), start=1):
        payload = [review.model_dump() for review in batch]
        response = client.responses.parse(
            model=model,
            instructions=(
                "You classify Russian-language customer reviews. "
                "For every input item, return exactly one result. Preserve each id exactly. "
                "Choose one sentiment and the single dominant topic. "
                "Use other only when no listed topic fits. Confidence must be from 0 to 1."
            ),
            input=json.dumps(payload, ensure_ascii=False),
            text_format=ReviewAnalysisBatch,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(f"Batch {batch_number}: the model returned no parsed output")

        expected_ids = [review.id for review in batch]
        actual_ids = [item.id for item in parsed.results]
        if len(actual_ids) != len(set(actual_ids)):
            raise RuntimeError(f"Batch {batch_number}: the model returned duplicate IDs")
        if set(actual_ids) != set(expected_ids):
            raise RuntimeError(
                f"Batch {batch_number}: expected IDs {expected_ids}, got {actual_ids}"
            )

        by_id = {item.id: item for item in parsed.results}
        analyses.extend(by_id[review_id] for review_id in expected_ids)

    return analyses


def save_result(path: Path, source: Path, model: str, results: list[ReviewAnalysis]) -> None:
    """Save validated results as readable UTF-8 JSON."""

    document = {
        "metadata": {
            "source_file": source.name,
            "model": model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "items_count": len(results),
        },
        "results": [item.model_dump() for item in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify reviews from CSV with an OpenAI model and save JSON."
    )
    parser.add_argument("--input", type=Path, default=Path("data/reviews.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/reviews_analysis.json"))
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--batch-size", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        print("Error: --batch-size must be at least 1", file=sys.stderr)
        return 2
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: set the OPENAI_API_KEY environment variable", file=sys.stderr)
        return 2

    try:
        reviews = load_reviews(args.input)
        results = analyze_reviews(OpenAI(), reviews, args.model, args.batch_size)
        save_result(args.output, args.input, args.model, results)
    except (OSError, ValueError, RuntimeError, OpenAIError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Saved {len(results)} classified reviews to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
