from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "platform-backend"
    database_url: str = "postgresql+psycopg2://mydata:mydata@localhost:5433/subscriptions_db"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3010,http://localhost:3110,http://localhost:3120"
    )
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "mydata"
    internal_api_token: str = "mydata-internal-dev-token"
    nats_url: str = ""
    poker_world_launch_url: str = "http://localhost:3110"
    product_allowed_origins: str = (
        "http://localhost:3010,http://localhost:3020,"
        "http://localhost:3030,http://localhost:3040,http://localhost:3050,"
        "http://localhost:3060,http://localhost:3070,http://localhost:3080,"
        "http://localhost:3090,http://localhost:3100,http://localhost:3110,"
        "http://localhost:3120"
    )
    bootstrap_admin_username: str = ""
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    # Platform-issued JWT issuer (ADR 0010). Override to keep Keycloak temporarily if needed.
    auth_issuer: str = "http://localhost:8002/v1/auth"
    use_platform_auth: bool = True
    handoff_ttl_seconds: int = 60

    @property
    def jwks_url(self) -> str:
        if self.use_platform_auth:
            return f"{self.auth_issuer.rstrip('/')}/jwks"
        return (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/certs"
        )

    @property
    def issuer(self) -> str:
        if self.use_platform_auth:
            return self.auth_issuer
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    def validate_bootstrap_config(self) -> None:
        values = (
            self.bootstrap_admin_username,
            self.bootstrap_admin_email,
            self.bootstrap_admin_password,
        )
        if any(values) and not all(values):
            raise ValueError(
                "Bootstrap admin username, email, and password must be provided together"
            )

    class Config:
        env_file = ".env"


settings = Settings()
