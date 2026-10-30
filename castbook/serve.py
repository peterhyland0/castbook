"""Deployable API: `modal deploy -m castbook.serve` (needs a `castbook-api` secret with CASTBOOK_API_TOKEN).

Kept out of castbook.entry so `modal run` commands don't require the secret.
"""

import os
from pathlib import Path

import modal

import castbook.entry  # noqa: F401  registers every function on the app
from castbook.workers.common import ARTIFACTS_DIR, app, artifacts_vol, service_image


@app.function(
    image=service_image,
    volumes={ARTIFACTS_DIR: artifacts_vol},
    secrets=[modal.Secret.from_name("castbook-api", required_keys=["CASTBOOK_API_TOKEN"])],
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def api():
    from castbook.api import create_app
    from castbook.multishot import run_request
    from castbook.state import ModalDictState
    from castbook.store import LocalStore
    from castbook.workers.judge import Judge

    judge = Judge()
    return create_app(
        state=ModalDictState(),
        store=LocalStore(ARTIFACTS_DIR),
        artifacts_root=Path(ARTIFACTS_DIR),
        launch=lambda request_id: run_request.spawn(request_id),
        embed=lambda image: judge.embed.remote(image),
        api_token=os.environ["CASTBOOK_API_TOKEN"],
        refresh=artifacts_vol.reload,
    )
