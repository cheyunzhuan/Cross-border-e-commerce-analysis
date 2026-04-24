import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


STOPWORDS = {
    "a", "about", "after", "all", "almost", "also", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "best", "better",
    "but", "by", "can", "case", "cases", "charge", "charger", "chargers",
    "charging", "clear", "could", "daily", "design", "did", "do", "does",
    "dont", "easy", "even", "every", "everything", "feel", "feels", "few",
    "for", "from", "get", "good", "great", "had", "has", "have", "help",
    "highly", "holds", "how", "i", "if", "in", "into", "is", "it", "its",
    "ive", "just", "keep", "like", "lot", "magsafe", "make", "makes", "me",
    "my", "nice", "not", "now", "of", "on", "one", "only", "or", "other",
    "out", "over", "perfect", "phone", "pretty", "product", "protect",
    "protection", "really", "screen", "secure", "seems", "show", "shows",
    "simple", "since", "slim", "small", "so", "solid", "some", "still",
    "strong", "style", "than", "that", "the", "their", "them", "there",
    "these", "they", "this", "those", "through", "to", "too", "use", "used",
    "using", "very", "want", "was", "well", "while", "with", "without",
    "work", "works", "would", "you", "your",
}

PAINPOINT_PATTERNS = {
    "magnet_strength": [
        "magnet", "magsafe", "magnetic", "charger", "wallet", "car mount",
    ],
    "yellowing_material": [
        "yellow", "yellowing", "clear back", "cloudy", "discolor", "material",
    ],
    "drop_protection": [
        "drop", "shockproof", "protect", "protection", "corner", "bumper",
        "raised edge", "raised edges", "camera lip",
    ],
    "fit_and_grip": [
        "slim", "bulk", "bulky", "grip", "hold", "pocket", "slippery",
    ],
    "buttons_cutouts": [
        "button", "buttons", "cutout", "cutouts", "port", "ports", "mute",
        "camera control",
    ],
    "camera_screen": [
        "camera", "lens", "screen", "edge", "edges", "lip",
    ],
}


def fix_mojibake(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if not text:
        return ""
    suspicious = ("â", "Ã", "ð", "™", "œ", "€", "Ù", "Ø")
    if any(ch in text for ch in suspicious):
        for _ in range(2):
            try:
                fixed = text.encode("latin1").decode("utf-8")
                if fixed and fixed != text:
                    text = fixed
                else:
                    break
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
    replacements = {
        "â€™": "'",
        "â€˜": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": "-",
        "â€": '"',
        "â€¦": "...",
        "Â": "",
        "ï¸�": "",
        "â˜º": "",
    }
    for src, target in replacements.items():
        text = text.replace(src, target)
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_mostly_english(text: str, threshold: float = 0.75) -> bool:
    if not text:
        return False
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    ascii_letters = sum(1 for ch in letters if "a" <= ch.lower() <= "z")
    return (ascii_letters / len(letters)) >= threshold


def looks_garbled(text: str) -> bool:
    if not text:
        return True
    bad_markers = ("ã", "�", "Ù", "Ø", "Ã", "â", "ð")
    if any(marker in text for marker in bad_markers):
        return True
    return False


def parse_rating(value: str) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None


def clean_tokenize(text: str) -> list[str]:
    text = fix_mojibake(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [token for token in text.split() if len(token) > 2 and token not in STOPWORDS]


def extract_ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def classify_painpoints(text: str) -> set[str]:
    lowered = fix_mojibake(text).lower()
    hits = set()
    for label, keywords in PAINPOINT_PATTERNS.items():
        if any(keyword in lowered for keyword in keywords):
            hits.add(label)
    return hits


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean_reviews(raw_rows: list[dict]) -> tuple[list[dict], dict]:
    cleaned = []
    dropped = {
        "empty_review_text": 0,
        "garbled_or_non_english": 0,
    }
    for row in raw_rows:
        review_text = fix_mojibake(row.get("review_text", ""))
        review_title = fix_mojibake(row.get("review_title", ""))
        if not review_text:
            dropped["empty_review_text"] += 1
            continue
        combined_text = f"{review_title} {review_text}".strip()
        if looks_garbled(combined_text) or not is_mostly_english(combined_text):
            dropped["garbled_or_non_english"] += 1
            continue
        rating_value = parse_rating(row.get("review_rating_text", ""))
        helpful_text = fix_mojibake(row.get("helpful_text", ""))
        helpful_count = 0
        match = re.search(r"(\d+)", helpful_text)
        if match:
            helpful_count = int(match.group(1))
        cleaned.append(
            {
                "ASIN": row.get("ASIN", ""),
                "review_id": row.get("review_id", ""),
                "review_page": row.get("review_page", ""),
                "review_title": review_title,
                "review_rating_text": fix_mojibake(row.get("review_rating_text", "")),
                "review_rating_value": rating_value if rating_value is not None else "",
                "review_date": fix_mojibake(row.get("review_date", "")),
                "review_text": review_text,
                "review_char_length": len(review_text),
                "review_word_count": len(clean_tokenize(review_text)),
                "helpful_text": helpful_text,
                "helpful_count": helpful_count,
                "is_verified_purchase": fix_mojibake(row.get("is_verified_purchase", "")),
            }
        )
    return cleaned, dropped


def summarize_status(status_rows: list[dict]) -> dict:
    total = len(status_rows)
    captcha_rows = sum(1 for row in status_rows if str(row.get("is_captcha", "")).strip().lower() == "yes")
    trace_counts = Counter(row.get("status_trace", "") for row in status_rows)
    review_sum = 0
    for row in status_rows:
        try:
            review_sum += int(float(row.get("review_count", 0)))
        except (TypeError, ValueError):
            continue
    return {
        "total_asins_attempted": total,
        "captcha_rows": captcha_rows,
        "captcha_rate": round(captcha_rows / total, 4) if total else 0.0,
        "status_trace_top": dict(trace_counts.most_common(5)),
        "review_count_sum": review_sum,
    }


def build_analysis(cleaned_rows: list[dict], status_summary: dict, dropped_summary: dict) -> dict:
    asins = {row["ASIN"] for row in cleaned_rows}
    rating_counter = Counter()
    positive_tokens = Counter()
    negative_tokens = Counter()
    positive_bigrams = Counter()
    negative_bigrams = Counter()
    painpoint_counts = Counter()
    rating_lengths = defaultdict(list)

    for row in cleaned_rows:
        rating = row["review_rating_value"]
        if rating != "":
            rating_counter[str(rating)] += 1
            rating_lengths[str(rating)].append(row["review_char_length"])
        text = row["review_text"]
        tokens = clean_tokenize(text)
        bigrams = extract_ngrams(tokens, 2)
        if rating != "" and float(rating) >= 4.0:
            positive_tokens.update(tokens)
            positive_bigrams.update(bigrams)
        elif rating != "" and float(rating) <= 2.0:
            negative_tokens.update(tokens)
            negative_bigrams.update(bigrams)
        for label in classify_painpoints(text):
            painpoint_counts[label] += 1

    rating_length_summary = {
        rating: round(mean(lengths), 1) for rating, lengths in sorted(rating_lengths.items(), key=lambda x: float(x[0]))
    }
    verified_rate = round(
        sum(1 for row in cleaned_rows if str(row["is_verified_purchase"]).lower() == "yes") / len(cleaned_rows), 4
    ) if cleaned_rows else 0.0

    summary = {
        "review_stats": {
            "total_reviews": len(cleaned_rows),
            "unique_asins": len(asins),
            "avg_reviews_per_asin": round(len(cleaned_rows) / len(asins), 2) if asins else 0.0,
            "verified_purchase_rate": verified_rate,
            "avg_review_char_length": round(mean(row["review_char_length"] for row in cleaned_rows), 1) if cleaned_rows else 0.0,
            "avg_review_word_count": round(mean(row["review_word_count"] for row in cleaned_rows), 1) if cleaned_rows else 0.0,
        },
        "rating_distribution": dict(sorted(rating_counter.items(), key=lambda x: float(x[0]))),
        "positive_top_words": positive_tokens.most_common(20),
        "negative_top_words": negative_tokens.most_common(20),
        "positive_top_bigrams": positive_bigrams.most_common(15),
        "negative_top_bigrams": negative_bigrams.most_common(15),
        "painpoint_counts": dict(painpoint_counts.most_common()),
        "rating_length_summary": rating_length_summary,
        "crawl_status": status_summary,
        "cleaning_filters": dropped_summary,
    }

    top_positive = ", ".join(word for word, _ in positive_tokens.most_common(5))
    top_negative = ", ".join(word for word, _ in negative_tokens.most_common(5))
    top_painpoints = ", ".join(label for label, _ in painpoint_counts.most_common(4))
    summary["readme_summary"] = (
        f"Review analysis was conducted on {summary['review_stats']['total_reviews']} cleaned reviews from "
        f"{summary['review_stats']['unique_asins']} ASINs captured from Amazon review pages. "
        f"The sample is strongly positive-skewed ({summary['rating_distribution'].get('5.0', 0)} five-star reviews), "
        f"with high-frequency positive themes around {top_positive or 'overall product satisfaction'}. "
        f"Negative feedback is concentrated on {top_negative or 'a small set of edge-case complaints'}. "
        f"Across the sample, the most recurring concern clusters are {top_painpoints or 'general usability and protection'}. "
        f"During review crawling, captcha affected {status_summary['captcha_rows']} of "
        f"{status_summary['total_asins_attempted']} attempted ASINs "
        f"({round(status_summary['captcha_rate'] * 100, 1)}%), so the review insight section should be interpreted "
        f"as a sample-based analysis rather than full-category coverage."
    )
    return summary


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary_markdown(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Review Analysis Summary",
        "",
        "## Review Stats",
        "",
        f"- Total cleaned reviews: {summary['review_stats']['total_reviews']}",
        f"- Unique ASINs: {summary['review_stats']['unique_asins']}",
        f"- Average reviews per ASIN: {summary['review_stats']['avg_reviews_per_asin']}",
        f"- Verified purchase rate: {summary['review_stats']['verified_purchase_rate']}",
        f"- Average review length (chars): {summary['review_stats']['avg_review_char_length']}",
        f"- Average review length (words): {summary['review_stats']['avg_review_word_count']}",
        "",
        "## Cleaning Filters",
        "",
        f"- Dropped empty reviews: {summary['cleaning_filters']['empty_review_text']}",
        f"- Dropped garbled/non-English reviews: {summary['cleaning_filters']['garbled_or_non_english']}",
        "",
        "## Rating Distribution",
        "",
    ]
    for rating, count in summary["rating_distribution"].items():
        lines.append(f"- {rating} stars: {count}")
    lines.extend(["", "## Positive Top Words", ""])
    for word, count in summary["positive_top_words"][:15]:
        lines.append(f"- {word}: {count}")
    lines.extend(["", "## Negative Top Words", ""])
    for word, count in summary["negative_top_words"][:15]:
        lines.append(f"- {word}: {count}")
    lines.extend(["", "## Pain Point Counts", ""])
    for label, count in summary["painpoint_counts"].items():
        lines.append(f"- {label}: {count}")
    lines.extend(
        [
            "",
            "## Rating Comparison",
            "",
        ]
    )
    for rating, avg_len in summary["rating_length_summary"].items():
        lines.append(f"- {rating} stars average review length: {avg_len} chars")
    lines.extend(
        [
            "",
            "## Crawl Status Impact",
            "",
            f"- Attempted ASINs: {summary['crawl_status']['total_asins_attempted']}",
            f"- Captcha-hit ASINs: {summary['crawl_status']['captcha_rows']}",
            f"- Captcha rate: {round(summary['crawl_status']['captcha_rate'] * 100, 1)}%",
            f"- Reviews successfully collected: {summary['crawl_status']['review_count_sum']}",
            "",
            "## README Summary",
            "",
            summary["readme_summary"],
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and analyze Amazon review samples.")
    parser.add_argument(
        "--raw-reviews",
        default="/Users/cyz/cheche/Cross-border e-commerce analysis/asin_reviews_raw.csv",
        help="Path to asin_reviews_raw.csv",
    )
    parser.add_argument(
        "--crawl-status",
        default="/Users/cyz/cheche/Cross-border e-commerce analysis/asin_review_crawl_status.csv",
        help="Path to asin_review_crawl_status.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("/Users/cyz/cheche/Cross-border e-commerce analysis") / "review_analysis_outputs"),
        help="Directory for cleaned data and analysis outputs",
    )
    args = parser.parse_args()

    raw_rows = read_csv_rows(Path(args.raw_reviews))
    status_rows = read_csv_rows(Path(args.crawl_status))
    cleaned_rows, dropped_summary = clean_reviews(raw_rows)
    status_summary = summarize_status(status_rows)
    summary = build_analysis(cleaned_rows, status_summary, dropped_summary)

    output_dir = Path(args.output_dir)
    write_csv(output_dir / "asin_reviews_cleaned.csv", cleaned_rows)
    (output_dir / "review_analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_summary_markdown(output_dir / "review_analysis_summary.md", summary)

    print("Review analysis completed.")
    print(f"Cleaned reviews saved to: {output_dir / 'asin_reviews_cleaned.csv'}")
    print(f"Summary JSON saved to: {output_dir / 'review_analysis_summary.json'}")
    print(f"Summary Markdown saved to: {output_dir / 'review_analysis_summary.md'}")
    print("")
    print("Review Stats:")
    for key, value in summary["review_stats"].items():
        print(f"- {key}: {value}")
    print("")
    print("Cleaning Filters:")
    for key, value in summary["cleaning_filters"].items():
        print(f"- {key}: {value}")
    print("")
    print("Rating Distribution:")
    for key, value in summary["rating_distribution"].items():
        print(f"- {key}: {value}")
    print("")
    print("Top Positive Words:")
    print(", ".join(f"{word}({count})" for word, count in summary["positive_top_words"][:10]))
    print("Top Negative Words:")
    print(", ".join(f"{word}({count})" for word, count in summary["negative_top_words"][:10]))
    print("")
    print("Pain Point Counts:")
    for key, value in summary["painpoint_counts"].items():
        print(f"- {key}: {value}")
    print("")
    print("README Summary:")
    print(summary["readme_summary"])


if __name__ == "__main__":
    main()
