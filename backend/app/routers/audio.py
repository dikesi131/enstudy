import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.database import get_db
from app.schemas import SentenceTTSRequest

router = APIRouter(prefix="/audio", tags=["audio"])


def _resolve_piper_model_path(config_path: str) -> str | None:
	raw = (config_path or "").strip()
	if not raw:
		return None

	backend_dir = Path(__file__).resolve().parents[2]
	repo_root = backend_dir.parent
	path_obj = Path(raw)

	candidates: list[Path] = []
	if path_obj.is_absolute():
		candidates.append(path_obj)
	else:
		candidates.extend(
			[
				Path.cwd() / path_obj,
				backend_dir / path_obj,
				repo_root / path_obj,
			]
		)

	for candidate in candidates:
		if candidate.is_file():
			return str(candidate)

		if candidate.is_dir():
			models = sorted(candidate.glob("*.onnx"))
			if models:
				return str(models[0])

	return None


def _resolve_piper_executable(config_value: str) -> str | None:
	raw = (config_value or "").strip()
	backend_dir = Path(__file__).resolve().parents[2]

	# 1) Respect explicit path-like configuration when possible.
	if raw:
		configured_path = Path(raw)
		if configured_path.is_absolute() and configured_path.is_file():
			return str(configured_path)

		if any(sep in raw for sep in ("/", "\\")):
			for candidate in (Path.cwd() / configured_path, backend_dir / configured_path):
				if candidate.is_file():
					return str(candidate)

	# 2) Try command name in PATH.
	for command_name in (raw or "piper", "piper", "piper.exe"):
		resolved = shutil.which(command_name)
		if resolved:
			return resolved

	# 3) Common local venv locations.
	for candidate in (
		backend_dir / ".venv" / "Scripts" / "piper.exe",
		backend_dir / ".venv" / "bin" / "piper",
	):
		if candidate.is_file():
			return str(candidate)

	return None


@router.get("/word/{word}")
def get_word_audio(word: str):
	encoded = quote(word)
	return {"url": f"http://dict.youdao.com/dictvoice?type=0&audio={encoded}"}


@router.post("/sentence")
def generate_sentence_tts(payload: SentenceTTSRequest, db: Session = Depends(get_db)):
	if not settings.piper_model_path:
		raise HTTPException(status_code=501, detail="PIPER_MODEL_PATH is not configured")

	model_path = _resolve_piper_model_path(settings.piper_model_path)
	if not model_path:
		raise HTTPException(
			status_code=500,
			detail=(
				"Piper model file does not exist. "
				f"Configured path: {settings.piper_model_path}"
			),
		)

	entry = None
	sentence_text = (payload.text or "").strip()
	target_path = None

	if payload.entry_id:
		entry = crud.get_entry_by_id(db, payload.entry_id)
		if not entry:
			raise HTTPException(status_code=404, detail="Entry not found")
		if not sentence_text:
			sentence_text = (getattr(entry, "sentence", "") or "").strip()

		cached_audio_path = getattr(entry, "sentence_audio_path", None)
		if cached_audio_path:
			existing_path = Path(str(cached_audio_path))
			if existing_path.exists():
				return FileResponse(path=str(existing_path), media_type="audio/wav", filename=existing_path.name)

	if not sentence_text:
		raise HTTPException(status_code=400, detail="Sentence text is required")

	# Normalize common invisible spaces copied from documents/web pages.
	sentence_text = sentence_text.replace("\u00a0", " ")

	final_dir = Path(__file__).resolve().parents[2] / "generated_audio"
	final_dir.mkdir(parents=True, exist_ok=True)

	if entry and getattr(entry, "sentence_audio_path", None):
		target_path = Path(str(getattr(entry, "sentence_audio_path")))
	elif entry:
		target_path = final_dir / f"entry_{int(getattr(entry, 'id'))}_{uuid4().hex[:8]}.wav"
	else:
		target_path = final_dir / f"sentence_{uuid4().hex[:8]}.wav"

	with tempfile.TemporaryDirectory() as tmp_dir:
		output_path = os.path.join(tmp_dir, "sentence.wav")
		piper_executable = _resolve_piper_executable(settings.piper_executable)
		if not piper_executable:
			raise HTTPException(
				status_code=500,
				detail=(
					"Piper executable not found. "
					f"Configured value: {settings.piper_executable}"
				),
			)

		cmd = [
			piper_executable,
			"--model",
			model_path,
			"--output_file",
			output_path,
		]

		try:
			subprocess.run(
				cmd,
				input=sentence_text,
				text=True,
				encoding="utf-8",
				capture_output=True,
				check=True,
			)
		except FileNotFoundError as exc:
			raise HTTPException(
				status_code=500,
				detail=f"Piper executable not found: {piper_executable}",
			) from exc
		except subprocess.CalledProcessError as exc:
			message = exc.stderr.strip() or "Piper TTS failed"
			raise HTTPException(status_code=500, detail=message) from exc

		if not os.path.exists(output_path):
			raise HTTPException(status_code=500, detail="TTS audio was not generated")

		with open(output_path, "rb") as src, open(target_path, "wb") as dst:
			dst.write(src.read())

		if entry:
			crud.set_entry_sentence_audio_path(db, int(getattr(entry, "id")), str(target_path))

		return FileResponse(path=str(target_path), media_type="audio/wav", filename=target_path.name)
