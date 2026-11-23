"""Opt-in fixture round-trip through Physis-next, never its production store."""
import hashlib
import json
import os
import subprocess

from .occluded_evidence import digest


class Physis:
    def __init__(self, binary, output):
        self.binary = binary
        self.world = output / "physis-world"
        self.world.mkdir()

    def _calls(self, calls):
        client = {"protocolVersion": "2025-06-18", "capabilities": {},
                  "clientInfo": {"name": "occluded-evidence-fixture", "version": "1"}}
        requests = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": client},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"}]
        requests += [
            {"jsonrpc": "2.0", "id": i, "method": "tools/call",
             "params": {"name": f"physis.{tool}", "arguments": arguments}}
            for i, (tool, arguments) in enumerate(calls, 1)
        ]
        env = {k: v for k, v in os.environ.items() if not k.startswith("PHYSIS_")}
        env["PHYSIS_STORE_DIR"] = str(self.world / ".physis-next")
        result = subprocess.run(
            [str(self.binary), "serve", "--stdio", "--path", str(self.world)],
            cwd=self.world, env=env, input="".join(json.dumps(r) + "\n" for r in requests),
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode:
            raise RuntimeError(f"local Physis exited {result.returncode}: {result.stderr[-300:]}")
        responses = [json.loads(line) for line in result.stdout.splitlines() if line]
        by_id = {r["id"]: r for r in responses if "id" in r}
        if (len(by_id) != len(calls) + 1
                or by_id.get(0, {}).get("result", {}).get("serverInfo", {}).get("name") != "physis"):
            raise RuntimeError("Physis stdio handshake or response count failed")
        values = []
        for i, (tool, _) in enumerate(calls, 1):
            response = by_id.get(i, {}).get("result", {})
            if response.get("isError") or "structuredContent" not in response:
                raise RuntimeError(f"Physis refused {tool}")
            values.append(response["structuredContent"])
        return values

    @staticmethod
    def _note(phase, record):
        return ("remember", {"actor": f"occluded-{phase}", "outcome": "unverified",
                             "text": json.dumps({"sha256": digest(record), "record": record})})

    @staticmethod
    def _subject(phase):
        return f"note:occluded-{phase}:unverified"

    @staticmethod
    def _evidence(hypothesis, phase, polarity, claim):
        return ("hypothesis.evidence", {"id": hypothesis, "polarity": polarity,
                                        "source": Physis._subject(phase), "claim": claim})

    def before(self, calibration, commitment):
        proposals = self._calls([
            ("hypothesis.propose", {"statement": f"Fixture transverse acceleration is {law}/8"})
            for law in (0, -1, 1)
        ])
        if any(item["status"] != "candidate" for item in proposals):
            raise RuntimeError("hypotheses must start as candidates")
        ids = {law: item["id"] for law, item in zip((0, -1, 1), proposals)}
        c, p, _ = self._calls([
            self._note("calibration", calibration), self._note("commitment", commitment),
            self._evidence(ids[0], "calibration", "contradicts",
                           "Measured displacement magnitude 45/8; nominal predicts zero"),
        ])
        return (ids, {"calibration": c["seq"], "commitment": p["seq"]},
                {"calibration": digest(calibration), "commitment": digest(commitment)})

    def after(self, anchors, observation, decision, verified):
        if type(verified) is not int or verified not in (-1, 1):
            raise ValueError("no verified resolution to attach")
        ids, seqs, hashes = anchors
        o, d, *_ = self._calls([
            self._note("acquisition", observation), self._note("decision", decision),
            self._evidence(ids[verified], "acquisition", "supports",
                           "Executed signed displacement matches this rival"),
            self._evidence(ids[-verified], "acquisition", "contradicts",
                           "Executed signed displacement disagrees with this rival"),
        ])
        seqs = {**seqs, "acquisition": o["seq"], "decision": d["seq"]}
        hashes = {**hashes, "acquisition": digest(observation), "decision": digest(decision)}
        log = self.world / ".physis-next" / "observations.jsonl"
        baseline = log.read_bytes()
        phases = list(seqs)
        records = self._calls(
            [("subject", {"subject": self._subject(phase)}) for phase in phases]
            + [("hypothesis.graph", {"id": hypothesis}) for hypothesis in ids.values()]
        )
        if log.read_bytes() != baseline or list(seqs.values()) != sorted(set(seqs.values())):
            raise RuntimeError("round-trip changed the ledger or reordered the proof")
        for phase, item in zip(phases, records):
            rows = item["rows"]
            if len(rows) != 1 or rows[0]["seq"] != seqs[phase]:
                raise RuntimeError(f"Physis did not reopen the {phase} evidence")
            saved = json.loads(rows[0]["body"])
            if digest(saved["record"]) != saved["sha256"] or saved["sha256"] != hashes[phase]:
                raise RuntimeError(f"Physis reopened a different {phase} record")
        verdicts = {}
        for law, graph in zip(ids, records[len(phases):]):
            status = "supported" if law == verified else "contradicted"
            phase = "calibration" if law == 0 else "acquisition"
            polarity = "supports" if law == verified else "contradicts"
            chain = graph["chain"]
            if len(chain) != 2 or graph["status"] != status:
                raise RuntimeError(f"wrong reopened hypothesis status for {law}")
            evidence = json.loads(chain[-1]["body"])
            if (evidence["source"], evidence["polarity"]) != (self._subject(phase), polarity):
                raise RuntimeError(f"wrong evidence binding for {law}")
            verdicts[str(law)] = {"id": graph["id"], "status": status,
                                  "evidence_seq": chain[-1]["seq"], "source": evidence["source"]}
        return {"scope": "disposable Physis stdio store", "observation_seqs": seqs,
                "hypotheses": verdicts, "log_sha256": hashlib.sha256(baseline).hexdigest(),
                "authority": "NOT_EVALUATED"}
