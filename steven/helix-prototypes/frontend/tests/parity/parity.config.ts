// Visual parity kit defaults (UI step 0). Rationale: tests/parity/README.md.

/** Both sides render at this CSS viewport with deviceScaleFactor 1. */
export const VIEWPORT = { width: 1440, height: 900 } as const;

/**
 * pixelmatch per-pixel YIQ color-distance threshold (0..1). 0.1 is the
 * pixelmatch default: it ignores sub-perceptual color noise while any real
 * token change (e.g. --hx-line vs --hx-line-soft) still counts.
 */
export const DEFAULT_PIXEL_THRESHOLD = 0.1;

/**
 * A screen FAILS when more than 1% of its compared (unmasked) pixels differ.
 * Anti-aliased pixels are excluded (includeAA: false). With the same fonts on
 * both sides, identical markup measures 0%; a 1px shift of one text line or a
 * wrong font weight in a component measures well above 1%.
 */
export const DEFAULT_MAX_DIFF_RATIO = 0.01;

export const DEFAULT_REFERENCE_FILE = "research/helix-e2e-workbench-v1.html";

export const BASE_URL = (process.env.HELIX_PARITY_BASE_URL ?? "http://127.0.0.1:3020").replace(/\/$/, "");
export const OUT_DIR = process.env.HELIX_PARITY_OUT ?? "../evidence/parity";
export const INCLUDE_PENDING = process.env.HELIX_PARITY_INCLUDE_PENDING === "1";
export const ONLY = (process.env.HELIX_PARITY_ONLY ?? "")
  .split(",")
  .map((id) => id.trim())
  .filter(Boolean);
