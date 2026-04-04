import os
from pathlib import Path


def _load_dotenv_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv_file()


class Settings:
    app_name: str = os.getenv("APP_NAME", "EnStudy API")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "enstudy")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "enstudy")
    mysql_db: str = os.getenv("MYSQL_DB", "enstudy")

    piper_executable: str = os.getenv("PIPER_EXECUTABLE", "piper")
    piper_model_path: str = os.getenv("PIPER_MODEL_PATH", "")
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    articles_dir: Path = Path(
        os.getenv(
            "ARTICLES_DIR",
            str(Path(__file__).resolve().parent.parent.parent / "articles"),
        )
    )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )


settings = Settings()
