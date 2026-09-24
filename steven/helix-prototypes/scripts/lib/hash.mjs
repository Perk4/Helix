// The two hash functions the qualification depends on, in one place.
//
// Both mirror `SectionRunService` in backend/app/section_runs.py so a Python
// reviewer and these scripts agree on a digest. Keeping one copy matters more
// than usual here: a certificate is only worth what a reviewer can recompute,
// and two implementations of the same digest drift the moment either is
// touched. The recorder and the verifier both import from here for that reason.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

/** Raw bytes of a file. Matches `SectionRunService._file_hash`. */
export const fileHash = (path) => `sha256:${createHash("sha256").update(readFileSync(path)).digest("hex")}`;

/** Sorted keys, compact separators. Matches `canonical_hash`. */
export const canonicalHash = (value) => {
  const canonical = (node) =>
    Array.isArray(node)
      ? node.map(canonical)
      : node && typeof node === "object"
        ? Object.fromEntries(Object.keys(node).sort().map((key) => [key, canonical(node[key])]))
        : node;
  return `sha256:${createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex")}`;
};
