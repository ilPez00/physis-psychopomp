# Patch plan: `physis import --schema psychopomp.observation/1` (uncompiled)

Date: 2026-11-22. For `~/dev/physis-next-candidate` (clean tree, 27 crates,
`Cargo.toml` present, remote `giveaway → physis-computer.git`).

> **Why this lives in the psychopomp repo.** I could not commit it there. That
> checkout is on a **detached HEAD** (`796940562a`), its `.git` is malformed (a
> nested `.git` directory), its `refs/remotes/giveaway/main` points at the *older*
> release `201fcc373a` while the live remote main is `d1fa83af`, and objects for
> that head are **missing** from the local object store (939 commits reachable,
> `cat-file` on the remote head fails). Branching and pushing from such a tree would
> carry a history the remote never had, so I did not. The file is left uncommitted
> in that working tree **and** recorded here, where it is committed and backed up.

**Status: written, NOT compiled and NOT run.** The box this was written on had a
load average of **19.5** on 12 cores with 4 GB free, and the fleet rule is explicit
that a cargo build does not belong there. Everything below was read from the source
at this revision, so the API names are facts; the code is a proposal that its author
must build. Nothing in the tree was modified.

## Measured facts (from `physis-next-candidate`, read not guessed)

The row shape I could not establish yesterday is now read, not guessed:

```rust
// crates/physis-kernel/src/observation.rs
pub struct Observation {
    pub seq: u64,                      // monotonic per log, assigned by the store
    pub at: DateTime<Utc>,             // chrono, UTC
    pub duration_ms: Option<u64>,      // None = instant
    pub source: ObservationSource,     // free-form bucket: "fs", "git", … new strings
    pub subject: String,               // a path, a command, a commit hash, a symbol
    pub body: String,                  // FLAT on purpose: "structure is imposed later"
    pub produced_by: Option<String>,   // watcher walk-back address
}
```

- **The body is a flat `String`**, so psychopomp's typed `props` object goes in as
  serialized JSON text — no schema change needed on their side, and their own comment
  says structure is imposed later.
- **Append path**: `physis_store::append_observations(paths, items)` takes an
  iterator, assigns `seq` under a cross-process lock, and refuses a torn log
  (`observation_prefix` errors on a truncated tail rather than deleting evidence).
- **Log path**: `StorePaths::observations()` → `<root>/observations.jsonl`.
- **Privacy**: the store has no read path for observations in that module — it
  exposes append, batch append and the per-store lock. `subject`/`body` are fields
  the app itself renders, so masking stays app-owned.

## The change

One new CLI variant, in `apps/physis-cli/src/main.rs`, next to `Observe`:

```rust
/// Import an external observation export into this tree's log.
/// Validates the schema string before touching the store: a foreign version is
/// refused rather than coerced.
Import {
    /// Declared schema of the input, e.g. `psychopomp.observation/1`.
    #[arg(long)]
    schema: String,
    /// JSONL file; `-` reads stdin.
    file: PathBuf,
    #[arg(long, default_value_t = false)]
    dry_run: bool,
},
```

Dispatch (the arm's shape follows the existing `Observe` arm; the exact match
plumbing is theirs):

```rust
Command::Import { schema, file, dry_run } => {
    let root = physis_store::StorePaths::new(store_root_for(&env, "."));
    let receipt = physis_import::import_psychopomp(&root, &schema, &file, dry_run)?;
    print_receipt(json, &receipt);
}
```

A new module `crates/physis-store/src/psychopomp.rs` (or `physis-import`, if the
crate split prefers it):

```rust
use anyhow::{bail, Context};
use chrono::{DateTime, TimeZone, Utc};
use physis_kernel::observation::Observation;
use serde::Deserialize;
use std::io::{BufRead, BufReader};

#[derive(Deserialize)]
struct Record {
    schema: String,
    subject: String,
    kind: String,
    at: f64,
    props: serde_json::Value,
    provenance: serde_json::Value,
    evidence: String,
    seq: u64,
}

pub struct ImportReceipt {
    pub schema: String,
    pub rows_read: usize,
    pub rows_appended: usize,
    pub rows_skipped: usize,
    pub dry_run: bool,
}

pub const PSYCHOMPOMP_V1: &str = "psychopomp.observation/1";

pub fn import_psychopomp(
    paths: &physis_store::StorePaths,
    schema: &str,
    file: &std::path::Path,
    dry_run: bool,
) -> anyhow::Result<ImportReceipt> {
    if schema != PSYCHOMPOMP_V1 {
        bail!("unsupported schema {schema:?}; this importer understands only {PSYCHOMPOMP_V1:?}");
    }
    let reader: Box<dyn BufRead> = if file == std::path::Path::new("-") {
        Box::new(BufReader::new(std::io::stdin()))
    } else {
        Box::new(BufReader::new(
            std::fs::File::open(file).with_context(|| format!("open {}", file.display()))?,
        ))
    };

    // Deduplicate against what the log already holds, on (subject, provenance, seq):
    // re-importing the same export must add nothing.
    let (existing, truncated) = physis_store::load_observations(&paths.observations());
    if truncated {
        bail!("observation log has a torn tail; refusing to append over it");
    }
    let seen: std::collections::HashSet<String> = existing
        .iter()
        .filter_map(|o| o.produced_by.clone())
        .collect();

    let mut batch = Vec::new();
    let mut rows_read = 0usize;
    let mut rows_skipped = 0usize;
    for (n, line) in reader.lines().enumerate() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let rec: Record = serde_json::from_str(&line)
            .with_context(|| format!("line {} is not a psychopomp record", n + 1))?;
        if rec.schema != PSYCHOMPOMP_V1 {
            bail!("line {} declares schema {:?}", n + 1, rec.schema);
        }
        if rec.evidence != "OBSERVED" {
            // the producer never emits predictions; refuse rather than mislabel
            bail!("line {} carries evidence {:?}, not OBSERVED", n + 1, rec.evidence);
        }
        rows_read += 1;

        let key = format!("{}:{}:{}", rec.subject,
                          rec.provenance.get("config_sha256").and_then(|v| v.as_str()).unwrap_or("-"),
                          rec.seq);
        if seen.contains(&key) {
            rows_skipped += 1;
            continue;
        }

        let secs = rec.at.trunc() as i64;
        let nanos = ((rec.at.fract()) * 1e9).round() as u32;
        let at: DateTime<Utc> = Utc.timestamp_opt(secs, nanos)
            .single()
            .context("observation time out of range")?;

        let body = serde_json::json!({
            "kind": rec.kind,
            "props": rec.props,
            "provenance": rec.provenance,
            "seq": rec.seq,
        })
        .to_string();

        batch.push(
            Observation::new("psychopomp", rec.subject)
                .with_body(body)
                .by(key.clone()),
        );
    }

    let rows_appended = if dry_run {
        batch.len()
    } else {
        let written = physis_store::append_observations(paths, batch)?;
        written.len()
    };

    Ok(ImportReceipt {
        schema: schema.to_string(),
        rows_read,
        rows_appended,
        rows_skipped,
        dry_run,
    })
}
```

## Why these choices

- **`source = "psychopomp"`** — their `ObservationSource` comment says new sources are
  new strings, not migrations, so this needs no upstream change.
- **`subject` = the producer's `episode:<seed>:<episode>`** verbatim. Namespacing by
  root is the *caller's* business (their `roots` command already namespaces ids), and
  silently rewriting it here would make two imports indistinguishable.
- **`produced_by` = the dedup key.** Their field is documented as a walk-back address
  and is otherwise unused by this importer, so it carries
  `subject:config_sha256:seq` — which makes the "re-import adds zero rows" guarantee
  mechanical rather than a convention. **This is the one judgement call**, and if the
  owner would rather keep `produced_by` for provenance honesty, the alternative is a
  scan of existing bodies (slower, same semantics).
- **Refuse, don't coerce**: wrong schema, non-`OBSERVED` evidence, torn log. Each
  refusal is a case where appending would create plausible-looking wrong history.
- **`dry_run`** returns the count without writing, so the acceptance test can be run
  on a real world safely.

## Acceptance test (the producer side is already checked by
`scripts/export-contract-check.py` gate in the psychopomp repo)

1. `physis import --schema psychopomp.observation/1 --dry-run fixture.jsonl` reports
   `rows_read == 5`, `rows_appended == 5`, and writes nothing.
2. Import for real: `observations.jsonl` grows by exactly 5; every `source` is
   `psychopomp`; `subject` is `episode:0:0`.
3. Import again: `rows_skipped == 5`, log unchanged byte-for-byte.
4. `physis subject episode:0:0` shows the five observations in `seq` order.
5. Truncate the log mid-line and import: exit non-zero with the torn-tail message,
   and the file is not modified.

## Not done here

- **not compiled, not run, not committed** — build gate is `cargo check -p
  physis-store` then `cargo test -p physis-store`, on a box with headroom;
- the `store_root_for` helper is a placeholder: their CLI resolves the store through
  `physis_config`/`--branch`, which I did not trace;
- no JSON output wiring for the receipt (their `json` flag pattern exists but its
  per-command renderer is theirs);
- no unit metadata: psychopomp emits box units and says so by omission, so the body
  carries no unit claim and a consumer must not invent one.
