"""
ingest_projects.py
Đọc PDF từ các thư mục PROJECT_CONTEXT của từng dự án, extract text, lưu ra JSON
để Antigravity đọc và ingest vào wiki.

Usage: python ingest_projects.py
Output: ./project_contexts.json
"""

import json
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz

TASKS_ROOT = Path(r"C:\Users\AnhDN63\OneDrive - FPT Corporation\@NA\3. Tasks")

# Các project cần xử lý (folder name → project key)
PROJECTS = {
    "3. Densys_Rulebase":      "densys-rulebase",
    "6. Densys_KMS_AI":        "densys-kms-ai",
    "7. Densys_OralAge":       "densys-oralage",
    "8. CU":                   "cu-central-uni",
    "9. DENSYS_ConsultantAI":  "densys-consultant-ai",
}

# Thư mục con bỏ qua (quá nhiều data raw)
SKIP_PATTERNS = [
    "\\raw\\", "bone_loss", ".venv", "site-packages",
    "\\400 meeting", "\\BK\\", "\\W1\\", "\\W2\\", "\\W3\\", "\\W4\\",
    "\\W5\\", "\\W6\\", "\\W7\\", "\\W8\\", "\\W9\\", "\\W10\\", "\\W11\\",
    "\\W12\\", "matplotlib",
]

MAX_CHARS_PER_FILE = 8000   # Giới hạn text mỗi file


def should_skip(path: Path) -> bool:
    p = str(path)
    return any(pat in p for pat in SKIP_PATTERNS)


def extract_pdf_text(pdf_path: Path, max_chars: int = MAX_CHARS_PER_FILE) -> str:
    try:
        doc = fitz.open(str(pdf_path))
        texts = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()
        full = "\n".join(texts).strip()
        if len(full) > max_chars:
            full = full[:max_chars] + f"\n\n...[truncated at {max_chars} chars]"
        return full
    except Exception as e:
        return f"[ERROR reading PDF: {e}]"


def main():
    results = {}

    for folder_name, project_key in PROJECTS.items():
        project_dir = TASKS_ROOT / folder_name
        context_dir = project_dir / "PROJECT_CONTEXT"

        if not context_dir.exists():
            print(f"  ⚠ No PROJECT_CONTEXT in: {folder_name}")
            continue

        print(f"\n📁 Processing: {folder_name}")
        pdfs = [
            p for p in context_dir.rglob("*.pdf")
            if not should_skip(p)
        ]

        if not pdfs:
            print(f"  ⚠ No PDFs found")
            continue

        print(f"  Found {len(pdfs)} PDFs")
        project_docs = []

        for pdf in sorted(pdfs):
            print(f"  📄 {pdf.name[:60]}...", end=" ")
            text = extract_pdf_text(pdf)
            word_count = len(text.split())
            if word_count < 20:
                print(f"⏩ skip (too short: {word_count} words)")
                continue

            project_docs.append({
                "filename": pdf.name,
                "path": str(pdf.relative_to(TASKS_ROOT)),
                "text": text,
                "words": word_count,
            })
            print(f"✓ ({word_count} words)")

        results[project_key] = {
            "folder": folder_name,
            "docs": project_docs,
        }

    # Lưu ra file JSON
    out = Path(__file__).parent / "project_contexts.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Saved to: {out}")
    print(f"   Projects: {list(results.keys())}")
    total = sum(len(v['docs']) for v in results.values())
    print(f"   Total PDFs processed: {total}")


if __name__ == "__main__":
    main()
