"""Run on the SOFY client host to retrieve this experiment's own artifacts."""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import shlex
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--remote-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    from sofy.cli.client_cmds import _post_debug_shell, _resolve_job_target
    _, url, login = _resolve_job_target(args.job_name)

    def execute(script, timeout=60):
        argv = ["python3", "-c", script]
        response = _post_debug_shell({"target": "master", "argv": argv, "timeout_seconds": timeout},
                                     legacy_cmd=shlex.join(argv), base_url=url, login_user=login)
        results = list(response.get("results", {}).values())
        if len(results) != 1:
            raise RuntimeError("expected exactly one SOFY master response")
        result = results[0]
        if result["exit_code"] or any(result.get("truncated", {}).values()):
            raise RuntimeError(f"transfer command failed or truncated: {result.get('stderr', '')[-1000:]}")
        return result["stdout"]

    # Reuse the official authenticated HTTP transport. Keep each response below
    # its 256 KiB diagnostic limit; never print payloads or export credentials.
    script = f'''
import pathlib,tarfile,hashlib,json,tempfile
root=pathlib.Path({args.remote_root!r})
files=[]
for folder in [*root.glob("large-ppo-b[0-3]"),root/"acceptance",root/"arena-primary",root/"arena-secondary"]:
    if folder.is_dir():
        files.extend(p for p in folder.rglob("*") if p.is_file() and p.suffix in (".pt",".json") and not any(x.endswith("-shards") for x in p.parts))
if not files or sum(p.stat().st_size for p in files)>250_000_000:
    raise ValueError("unexpected artifact size")
with tempfile.NamedTemporaryFile(dir=root,prefix="mahjong-transfer-",suffix=".tar.gz",delete=False) as tmp:
    path=pathlib.Path(tmp.name)
with tarfile.open(path,mode="w:gz") as archive:
    for p in sorted(files): archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
print(json.dumps({{"files":len(files),"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"remote_archive":str(path)}}))
'''
    meta = json.loads(execute(script, timeout=120))
    if not 0 < meta["bytes"] <= 250_000_000:
        raise ValueError("unexpected archive size")
    print(json.dumps(meta), flush=True)
    block = 128 * 1024

    def read_chunk(offset):
        code = f"import base64; f=open({meta['remote_archive']!r},'rb'); f.seek({offset}); print(base64.b64encode(f.read({block})).decode())"
        raw = base64.b64decode(execute(code).strip(), validate=True)
        if len(raw) != min(block, meta["bytes"] - offset):
            raise ValueError("short artifact chunk")
        return raw

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        data = b"".join(pool.map(read_chunk, range(0, meta["bytes"], block)))
    if len(data) != meta["bytes"] or hashlib.sha256(data).hexdigest() != meta["sha256"]:
        raise ValueError("artifact checksum mismatch")
    args.output.write_bytes(data)
    args.output.with_suffix(args.output.suffix + ".json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({"output": str(args.output), **meta}), flush=True)


if __name__ == "__main__":
    main()
