"""Start the preserved V3 same-origin POST server in a new consumer workspace.

No browser automation, kernel changes, or original private CPU authorization is
used. This explicitly creates a new local consumer measurement profile.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main(project):
    project = Path(project).resolve()
    base = project / "outputs/claude_round2_2026-11-17/science/compute"
    source = base / "serve_browser_v3.py"
    name = "preserved_v3_loopback_server"
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    result = base / "browser_consumer_v3_01"
    if result.exists():
        raise FileExistsError("Use another new workspace for a new browser observation")
    module.RESULT_DIR = result
    policy = module.production_policy()
    profile = dict(schema="consumer-browser-v3-profile/1", created_utc=datetime.now(timezone.utc).isoformat(),
                   source_server_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   manifest=policy.manifest, cells=24, per_worker_cap_seconds=120,
                   endpoint=module.ENDPOINT, body_limit_bytes=module.MAX_BYTES,
                   numerical_sources_modified=False, private_original_authorization_used=False,
                   profile="New consumer observation; not the original manuscript timing run")
    (project.parent / "CONSUMER_BROWSER_PROFILE.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    server = module.make_server(policy)
    server.timeout = .5
    port = server.server_address[1]
    print(json.dumps(dict(status="MANUAL_BROWSER_V3_READY", url=f"http://127.0.0.1:{port}/v3/",
        endpoint=module.ENDPOINT, output_project_path="outputs/claude_round2_2026-11-17/science/compute/browser_consumer_v3_01/observed.json",
        transport="same-origin-loopback-post-v3", cells=24, cap_seconds=120,
        stop="Ctrl+C after persistence; byte-identical POST retry is idempotent, a different body is refused")), flush=True)
    try:
        server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
