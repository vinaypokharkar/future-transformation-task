from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    jwt_secret_key: str = "change-me"
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
