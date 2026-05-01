"""
convert_to_kb.py  (v3 – with image extraction)
Batch convert PPT/Excel → Markdown + extract ảnh thành local URL
Mở bằng VS Code / Obsidian / Typora → click ảnh xem trực tiếp

Usage: python convert_to_kb.py --input ./your_folder --output ./knowledge_base
"""

import argparse, hashlib, shutil
from pathlib import Path

def install_deps():
    import subprocess, sys
    pkgs = ["python-pptx", "openpyxl", "pandas", "Pillow"]
    subprocess.check_call([sys.executable, "-m", "pip", "install", *pkgs, "-q"])

try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    import openpyxl
    from PIL import Image
    import io
except ImportError:
    print("Installing dependencies...")
    install_deps()
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    import openpyxl
    from PIL import Image
    import io


# ══════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════

def save_image_blob(blob: bytes, images_dir: Path, prefix: str) -> str:
    """
    Lưu image blob vào images_dir, trả về relative path dạng
    ./images/<prefix>_<hash8>.png  (dedup bằng hash)
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    ext = _detect_ext(blob)
    h   = hashlib.md5(blob).hexdigest()[:8]
    filename = f"{prefix}_{h}{ext}"
    dest = images_dir / filename
    if not dest.exists():
        dest.write_bytes(blob)
    return f"./images/{filename}"


def _detect_ext(blob: bytes) -> str:
    """Đoán extension từ magic bytes."""
    if blob[:4] == b'\x89PNG':
        return ".png"
    if blob[:3] == b'\xff\xd8\xff':
        return ".jpg"
    if blob[:4] in (b'GIF8', b'GIF9'):
        return ".gif"
    if blob[:4] == b'RIFF' and blob[8:12] == b'WEBP':
        return ".webp"
    return ".png"  # fallback


def runs_to_md(paragraph) -> str:
    parts = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        bold, italic = run.font.bold, run.font.italic
        if bold and italic:   text = f"***{text}***"
        elif bold:            text = f"**{text}**"
        elif italic:          text = f"*{text}*"
        parts.append(text)
    return "".join(parts)


def shape_table_to_md(table) -> str:
    rows = []
    for i, row in enumerate(table.rows):
        cells = [
            " ".join(p.text.strip() for p in cell.text_frame.paragraphs if p.text.strip()).replace("|", "\\|")
            for cell in row.cells
        ]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════
#  PPT → Markdown  (text + table + image)
# ══════════════════════════════════════════════════════

def pptx_to_markdown(filepath: Path, images_dir: Path) -> str:
    prs   = Presentation(filepath)
    lines = [f"# {filepath.stem}\n"]
    stem  = filepath.stem

    for slide_num, slide in enumerate(prs.slides, 1):
        lines.append(f"\n---\n## Slide {slide_num}")

        if slide.shapes.title and slide.shapes.title.text.strip():
            lines.append(f"### {slide.shapes.title.text.strip()}\n")

        img_counter = 0
        for shape in slide.shapes:

            # ── Hình ảnh ──
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    blob     = shape.image.blob
                    img_path = save_image_blob(blob, images_dir, f"{stem}_s{slide_num}_img{img_counter}")
                    alt      = shape.name or f"image_{img_counter}"
                    lines.append(f"\n![{alt}]({img_path})\n")
                    img_counter += 1
                except Exception as e:
                    lines.append(f"> *(Không thể extract ảnh: {e})*\n")
                continue

            # ── Group shape (có thể chứa ảnh bên trong) ──
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                for child in shape.shapes:
                    if child.shape_type == MSO_SHAPE_TYPE.PICTURE:
                        try:
                            blob     = child.image.blob
                            img_path = save_image_blob(blob, images_dir, f"{stem}_s{slide_num}_img{img_counter}")
                            alt      = child.name or f"image_{img_counter}"
                            lines.append(f"\n![{alt}]({img_path})\n")
                            img_counter += 1
                        except Exception:
                            pass
                continue

            # ── Table ──
            if shape.has_table:
                lines.append(shape_table_to_md(shape.table))
                lines.append("")
                continue

            # ── Text frame ──
            if not shape.has_text_frame:
                continue
            if shape == slide.shapes.title:
                continue

            for para in shape.text_frame.paragraphs:
                raw = para.text.strip()
                if not raw:
                    continue
                indent    = "  " * para.level
                formatted = runs_to_md(para) or raw
                lines.append(f"{indent}- {formatted}")

        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════
#  Excel → Markdown  (data + embedded images)
# ══════════════════════════════════════════════════════

def format_cell_value(cell) -> str:
    from datetime import datetime, date
    value = cell.value
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float)):
        fmt = cell.number_format or ""
        if "%" in fmt:
            return f"{value * 100:.1f}%"
        elif any(c in fmt for c in ["#,", "0,"]):
            return f"{value:,.0f}" if float(value) == int(value) else f"{value:,.2f}"
        elif "0.00" in fmt:
            return f"{value:.2f}"
        else:
            return str(int(value)) if float(value) == int(value) else str(value)
    return str(value).strip()


def xlsx_to_markdown(filepath: Path, images_dir: Path) -> str:
    wb    = openpyxl.load_workbook(filepath, data_only=True)
    lines = [f"# {filepath.stem}\n"]
    stem  = filepath.stem

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        if ws.max_row == 0 or ws.max_column == 0:
            continue

        lines.append(f"\n## Sheet: {sheet_name}")
        lines.append(f"*(Rows: {ws.max_row}, Columns: {ws.max_column})*\n")

        # ── Extract embedded images ──
        sheet_images = getattr(ws, '_images', [])
        if sheet_images:
            lines.append("**Hình ảnh trong sheet:**\n")
            for idx, img_obj in enumerate(sheet_images):
                try:
                    blob     = img_obj._data() if callable(img_obj._data) else img_obj._data
                    img_path = save_image_blob(blob, images_dir, f"{stem}_{sheet_name}_img{idx}")
                    lines.append(f"![image_{idx}]({img_path})\n")
                except Exception as e:
                    lines.append(f"> *(Không thể extract ảnh: {e})*\n")

        # ── Merged cells map ──
        merged_map = {}
        for rng in ws.merged_cells.ranges:
            master = ws.cell(rng.min_row, rng.min_col).value
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    if not (r == rng.min_row and c == rng.min_col):
                        merged_map[(r, c)] = str(master or "")

        # ── Table data ──
        table_rows = []
        for row in ws.iter_rows():
            row_data = []
            for cell in row:
                coord = (cell.row, cell.column)
                row_data.append(merged_map[coord] if coord in merged_map else format_cell_value(cell))
            if any(v.strip() for v in row_data):
                table_rows.append(row_data)

        if not table_rows:
            lines.append("*(Sheet trống)*\n")
            continue

        header = table_rows[0]
        lines.append("| " + " | ".join(str(h).replace("|", "\\|") for h in header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in table_rows[1:]:
            while len(row) < len(header):
                row.append("")
            lines.append("| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |")
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════

CONVERTERS = {
    ".pptx": pptx_to_markdown,
    ".xlsx": xlsx_to_markdown,
    ".xls":  xlsx_to_markdown,
}

def convert_folder(input_dir: str, output_dir: str):
    input_path  = Path(input_dir)
    output_path = Path(output_dir)
    images_dir  = output_path / "images"   # tất cả ảnh lưu tập trung ở đây
    output_path.mkdir(parents=True, exist_ok=True)

    index_lines = ["# Knowledge Base Index\n"]
    converted, skipped = 0, 0

    for file in sorted(input_path.rglob("*")):
        ext = file.suffix.lower()
        if ext not in CONVERTERS:
            skipped += 1
            continue

        print(f"Converting: {file.name} ...", end=" ")
        try:
            md_content = CONVERTERS[ext](file, images_dir)
            out_file   = output_path / (file.stem + ".md")
            out_file.write_text(md_content, encoding="utf-8")

            preview = next(
                (l for l in md_content.splitlines() if l.strip() and not l.startswith("#")),
                ""
            )[:120]
            index_lines += [
                f"## {file.stem}",
                f"- **File gốc:** `{file.name}`",
                f"- **Loại:** {ext.lstrip('.')}",
                f"- **Preview:** {preview}",
                f"- **Markdown:** `{out_file.name}`\n",
            ]
            converted += 1
            print("✓")
        except Exception as e:
            print(f"✗  →  {e}")
            skipped += 1

    (output_path / "_INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

    img_count = len(list(images_dir.glob("*"))) if images_dir.exists() else 0
    print(f"\n✅ Done  : {converted} files converted, {skipped} skipped")
    print(f"🖼  Images: {img_count} extracted → {images_dir.resolve()}")
    print(f"📁 Output : {output_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True,                 help="Folder chứa file gốc")
    parser.add_argument("--output", default="./knowledge_base",    help="Folder output")
    args = parser.parse_args()
    convert_folder(args.input, args.output)