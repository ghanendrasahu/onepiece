"""Run the gateway: ``uv run --directory apps/gateway python -m worldview_gateway``.

Opts into TLS termination when GATEWAY_TLS_CERT_FILE and GATEWAY_TLS_KEY_FILE
are provided (e.g. a locally generated self-signed cert for a TLS demo).
"""

import uvicorn

from .config import get_gateway_settings


def main() -> None:
    from typing import Any

    settings = get_gateway_settings()
    tls: dict[str, Any] = {}
    if settings.tls_cert_file and settings.tls_key_file:
        tls["ssl_certfile"] = settings.tls_cert_file
        tls["ssl_keyfile"] = settings.tls_key_file
    uvicorn.run(
        "worldview_gateway.main:app",
        host="0.0.0.0",  # nosec B104
        port=settings.port,
        log_level=settings.log_level.lower(),
        **tls,
    )


if __name__ == "__main__":
    main()
