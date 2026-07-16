from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that ship in this repo or are obvious stand-ins. Anything here is
# public knowledge, so a token signed with one can be forged by anybody who has
# read the source.
_PLACEHOLDER_SECRETS = {
    "change-me",
    "changeme",
    "change-me-in-production-use-a-real-random-secret",
    "docker-demo-secret-not-for-production",
    "secret",
    "supersecret",
    "your-secret-key",
    "test",
}

# HS256 keys shorter than the hash output add no security over a 256-bit key and
# are usually a sign someone typed a word rather than generating one.
_MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "AI-Powered Task & Knowledge Management System"
    api_prefix: str = "/api/v1"

    database_url: str = "mysql+pymysql://km_user:km_pass@localhost:3306/knowledge_mgmt"
    test_database_url: str = (
        "mysql+pymysql://km_user:km_pass@localhost:3307/knowledge_mgmt_test"
    )

    # No default, deliberately. A working-but-weak default is the worst option
    # available: the app boots, every test passes, and every token is forgeable
    # by anyone who has read this file. Missing config should stop the process,
    # not silently downgrade its security.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: str = "uploads"
    max_upload_mb: int = 10

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    # Measured, not guessed. scripts/sweep_chunking.py evaluated 150-500 against
    # the calibration fixture; 400/50 is the only config that ranked all 7
    # paraphrase queries to the correct chunk. Smaller chunks fragmented facts
    # across boundaries; 500 merged unrelated policy sections into one chunk,
    # averaging several topics into an embedding that represented none of them.
    chunk_size: int = 400
    chunk_overlap: int = 50
    faiss_index_path: str = "data/faiss.index"
    search_top_k: int = 5
    # Measured by scripts/calibrate.py, not guessed: the midpoint between the
    # weakest true positive (0.2971) and the strongest true negative (0.2365).
    # See sample_docs/calibration_result.md.
    #
    # The +0.0606 separation is real but narrow, and it is tuned to this corpus.
    # A different document set should be re-calibrated rather than inheriting
    # this number. Near-miss queries (right topic, absent fact) score up to
    # 0.4284 and are deliberately not gated — no floor can exclude them without
    # rejecting genuine answers first.
    similarity_floor: float = 0.2668

    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "Admin@123"
    seed_user_password: str = "User@123"

    @field_validator("jwt_secret_key")
    @classmethod
    def _reject_weak_secret(cls, v: str) -> str:
        """Refuse to start on a secret that anyone reading the repo would know.

        The placeholder in .env.example is caught here on purpose. Copying that
        file is step one of the README, so without this check the documented
        happy path hands you a publicly-known signing key — and nothing about
        the running app would look wrong.
        """
        hint = (
            'Generate one with:\n'
            '  python -c "import secrets; print(secrets.token_urlsafe(32))"\n'
            "then set JWT_SECRET_KEY in backend/.env"
        )

        if v.strip().lower() in _PLACEHOLDER_SECRETS:
            raise ValueError(
                f"JWT_SECRET_KEY is set to the placeholder {v!r}, which is public "
                f"in this repository — anyone could forge an admin token.\n{hint}"
            )
        if len(v) < _MIN_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY is {len(v)} characters; HS256 needs at least "
                f"{_MIN_SECRET_LENGTH}.\n{hint}"
            )
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
