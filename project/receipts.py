#!/usr/bin/env python3
"""Stage receipts. A changed input or parameter marks that stage and every
stage after it stale. Fresh stages are not re-run.

  python project/receipts.py plan project_dir --stage cut --input raw=raw.mov
"""
import argparse, hashlib, json, os

STAGE_ORDER = ["intake", "transcribe", "cut", "graphics", "sound", "finish", "checks"]
# A stage is downstream of the stages it reads. Sound is independent of the picture cut.
DEPENDS_ON = {
    "intake": [],
    "transcribe": ["intake"],
    "cut": ["transcribe"],
    "graphics": ["cut"],
    "sound": [],
    "finish": ["cut", "graphics", "sound"],
    "checks": ["finish"],
}
RECEIPT_NAME = "receipts.json"

def receipt_path(project_dir):
    return os.path.join(project_dir, RECEIPT_NAME)

def load_receipts(project_dir):
    path = receipt_path(project_dir)
    if not os.path.exists(path):
        return {"stages": {}}
    return json.load(open(path, encoding="utf-8"))

def save_receipts(project_dir, store):
    os.makedirs(project_dir, exist_ok=True)
    json.dump(store, open(receipt_path(project_dir), "w", encoding="utf-8"), indent=2)
    open(receipt_path(project_dir), "a", encoding="utf-8").write("\n")

def hash_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()

def hash_params(params):
    blob = json.dumps(params or {}, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()

def record(project_dir, stage, inputs, params, outputs):
    """inputs and outputs are {name: path}. Files must exist."""
    if stage not in STAGE_ORDER:
        raise ValueError(f"unknown stage {stage}")
    store = load_receipts(project_dir)
    store["stages"][stage] = {
        "inputs": {name: {"path": path, "sha256": hash_file(path)} for name, path in inputs.items()},
        "params": params or {},
        "params_sha256": hash_params(params),
        "outputs": {name: {"path": path, "sha256": hash_file(path)} for name, path in outputs.items()},
    }
    save_receipts(project_dir, store)
    return store["stages"][stage]

def _stage_dirty(record_stage, inputs, params):
    if record_stage is None:
        return True
    if record_stage.get("params_sha256") != hash_params(params):
        return True
    recorded_in = record_stage.get("inputs") or {}
    if set(recorded_in) != set(inputs):
        return True
    for name, path in inputs.items():
        if not os.path.exists(path):
            return True
        if hash_file(path) != recorded_in[name]["sha256"]:
            return True
    for item in (record_stage.get("outputs") or {}).values():
        if not os.path.exists(item["path"]):
            return True
    return False

def plan(project_dir, stages):
    """stages is an ordered list of {name, inputs, params} for the stages that exist.

    Returns the names that should re-run. A dirty stage dirties everything
    later in STAGE_ORDER that is also listed.
    """
    store = load_receipts(project_dir).get("stages") or {}
    by_name = {item["name"]: item for item in stages}
    stale = []
    stale_set = set()
    for name in STAGE_ORDER:
        if name not in by_name:
            continue
        item = by_name[name]
        own = _stage_dirty(store.get(name), item.get("inputs") or {}, item.get("params") or {})
        upstream = any(dep in stale_set for dep in DEPENDS_ON.get(name, []))
        if own or upstream:
            stale.append(name)
            stale_set.add(name)
    return stale

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("project_dir")
    rec.add_argument("--stage", required=True)
    rec.add_argument("--input", action="append", default=[], help="name=path")
    rec.add_argument("--output", action="append", default=[], help="name=path")
    rec.add_argument("--params")
    pl = sub.add_parser("plan")
    pl.add_argument("project_dir")
    pl.add_argument("--spec", required=True, help="JSON list of {name, inputs, params}")
    args = ap.parse_args(argv)
    if args.cmd == "record":
        def pairs(items):
            out = {}
            for item in items:
                name, path = item.split("=", 1)
                out[name] = path
            return out
        params = json.loads(args.params) if args.params else {}
        record(args.project_dir, args.stage, pairs(args.input), params, pairs(args.output))
        print("recorded", args.stage)
    else:
        spec = json.load(open(args.spec, encoding="utf-8"))
        print("\n".join(plan(args.project_dir, spec)))

if __name__ == "__main__":
    main()
