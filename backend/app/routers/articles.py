from datetime import datetime
from io import BytesIO
from pathlib import Path
import zipfile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pathvalidate import sanitize_filename

from app.config import settings

router = APIRouter(prefix="/articles", tags=["articles"])


def _ensure_articles_dir() -> Path:
    articles_dir = settings.articles_dir
    articles_dir.mkdir(parents=True, exist_ok=True)
    return articles_dir


def _normalize_filename(filename: str) -> str:
    cleaned = sanitize_filename(filename, replacement_text="_").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid file name")
    if not cleaned.lower().endswith(".md"):
        cleaned = f"{cleaned}.md"
    if cleaned == ".md":
        raise HTTPException(
            status_code=400,
            detail="Invalid markdown file name",
        )
    return cleaned


def _article_path(filename: str) -> Path:
    articles_dir = _ensure_articles_dir().resolve()
    normalized = _normalize_filename(filename)
    candidate = (articles_dir / normalized).resolve()
    if candidate.parent != articles_dir:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return candidate


def _extract_title(filename: str, content: str) -> str:
    for line in content.splitlines():
        text = line.strip()
        if text.startswith("#"):
            title = text.lstrip("#").strip()
            if title:
                return title
    return Path(filename).stem


@router.get("")
def list_articles():
    articles_dir = _ensure_articles_dir()
    items = []

    article_paths = sorted(
        articles_dir.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in article_paths:
        content = path.read_text(encoding="utf-8")
        stat = path.stat()
        items.append(
            {
                "filename": path.name,
                "title": _extract_title(path.name, content),
                "size": stat.st_size,
                "updated_at": datetime.fromtimestamp(
                    stat.st_mtime
                ).isoformat(),
            }
        )

    return {"items": items}


@router.post("/import")
async def import_articles(
    files: list[UploadFile] = File(...),
    overwrite: bool = Query(True),
):
    articles_dir = _ensure_articles_dir()

    imported = []
    skipped = []

    for file in files:
        if not file.filename:
            skipped.append({"filename": "", "reason": "missing filename"})
            continue

        normalized = _normalize_filename(file.filename)
        if not normalized.lower().endswith(".md"):
            skipped.append(
                {"filename": file.filename, "reason": "not markdown"}
            )
            continue

        target = (articles_dir / normalized).resolve()
        if target.parent != articles_dir.resolve():
            skipped.append(
                {"filename": file.filename, "reason": "invalid path"}
            )
            continue

        if target.exists() and not overwrite:
            skipped.append(
                {"filename": normalized, "reason": "already exists"}
            )
            continue

        raw = await file.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} is not UTF-8 encoded",
            ) from exc

        target.write_text(content, encoding="utf-8")
        imported.append(normalized)

    return {
        "ok": True,
        "imported_count": len(imported),
        "imported_files": imported,
        "skipped_count": len(skipped),
        "skipped_files": skipped,
    }


@router.get("/export-all")
def export_all_articles():
    articles_dir = _ensure_articles_dir()
    zip_buffer = BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zip_file:
        for path in sorted(articles_dir.glob("*.md")):
            zip_file.writestr(path.name, path.read_bytes())

    zip_buffer.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=articles-export.zip"
    }
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers=headers,
    )


@router.get("/{filename}")
def get_article(filename: str):
    path = _article_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Article not found")

    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "filename": path.name,
        "title": _extract_title(path.name, content),
        "content": content,
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


@router.get("/{filename}/export")
def export_article(filename: str):
    path = _article_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Article not found")

    return FileResponse(
        path,
        media_type="text/markdown; charset=utf-8",
        filename=path.name,
    )
