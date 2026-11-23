# R-P1.55 first run — instrument qualified after review

Frozen card: `bc950c77d5b2b79f9ca073972e318b923e97949b`.
Original script SHA-256:
`f8f0af023dcd99cbbb7bf1c025088d09371045db2ca00dc4025d439429909441`.
World: `/tmp/opencode/laned-2uz9xsdy`, `physis 1.9.1`.

- `claim` before: rc 2. Hardcoded `declare`: rc 0, admitted at seq 10.
- Log rows: 10 to 11. `claim` after: rc 0. The target file's relation
  count grew from one to two; its original edge still returned rc 0.
- Both `ontology-check --path` calls returned rc 2 with
  `unexpected argument '--path' found`. No ontology verdict was measured.
- The script printed all six checks upheld. It did not check both true edges
  before declaration, could pass Z6 with zero proposals, and did not take the
  declaration from the decoder output. Treat this as a direct writer probe,
  not a verified decoder-to-writer result.

Read-only follow-up on the same world confirmed that the fold cites `#10`
for the cross-file `DEFINES`, and the raw row at seq 10 has `source: host`
and `produced_by: physis declare`. A corrected invocation reported zero
structural violations **after** the write; the pilot had no valid before
measurement. These are post-hoc checks, not replacements for the pilot.
