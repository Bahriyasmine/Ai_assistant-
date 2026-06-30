import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logging import logger

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Settings loaded from the .env file via pydantic-settings.
    All secrets and environment-specific values live here.
    Non-sensitive config (instructions, questions, etc.) lives in config.yaml.

    Attributes:
        openai_api_key: OpenAI API key.
        openai_model: Model used for all Responses API calls.
        vector_store_id: OpenAI vector store ID (vs_xxx). Optional — falls back
                         to .vector_store_id file if not set in .env.
        data_dir: Directory containing knowledge-base documents.
        api_key: Key required on X-API-Key header. Empty string disables auth.
        config_path: Path to the YAML config file.
    """

    openai_api_key: str
    openai_model: str = "gpt-4o"
    vector_store_id: str = ""
    data_dir: str = "data"
    api_key: str = ""
    config_path: str = "core/config.yaml"

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"))

    @property
    def resolved_vector_store_id(self) -> str | None:
        """Returns vector_store_id from .env, falling back to .vector_store_id file."""
        if self.vector_store_id.strip():
            return self.vector_store_id.strip()
        id_file = BASE_DIR / ".vector_store_id"
        if id_file.exists():
            return id_file.read_text().strip() or None
        return None

    def save_vector_store_id(self, vs_id: str) -> None:
        """Persists a newly created vector store ID.

        Writes to two places:
        - .vector_store_id file: read dynamically on every request, works immediately
          without restarting the server.
        - .env file: updates VECTOR_STORE_ID line so the ID is visible and survives
          after a server restart.
        """
        (BASE_DIR / ".vector_store_id").write_text(vs_id)

        env_file = BASE_DIR / ".env"
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").splitlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("VECTOR_STORE_ID="):
                    lines[i] = f"VECTOR_STORE_ID={vs_id}"
                    updated = True
                    break
            if not updated:
                lines.append(f"VECTOR_STORE_ID={vs_id}")
            env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            env_file.write_text(f"VECTOR_STORE_ID={vs_id}\n", encoding="utf-8")

    @classmethod
    def load_settings(cls) -> "Settings":
        try:
            logger.info("Loading settings from environment...")
            return cls()
        except Exception as e:
            logger.error("Failed to load settings: %s", e)
            raise RuntimeError(f"Failed to load settings: {e}") from e


def load_yaml_config(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config is None:
            raise ValueError("YAML config is empty.")
        logger.info("Loaded config from %s", path)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file '{path}' not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML '{path}': {e}")


try:
    settings = Settings.load_settings()
    yaml_config = load_yaml_config(settings.config_path)
except Exception as e:
    print("Error loading config:", e)
    raise SystemExit(1)
