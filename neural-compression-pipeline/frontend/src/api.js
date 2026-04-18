const OCR_BASE = import.meta.env.VITE_OCR_URL ?? "http://localhost:8001";
const COMPRESS_BASE = import.meta.env.VITE_COMPRESS_URL ?? "http://localhost:8002";

function formatHttpError(status, data) {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((x) => (typeof x?.msg === "string" ? x.msg : JSON.stringify(x))).join("; ");
  }
  if (d && typeof d === "object") return JSON.stringify(d);
  return `Request failed (${status})`;
}

export async function fetchOcrHealth() {
  const r = await fetch(`${OCR_BASE}/health`);
  return r;
}

/** Validation/test accuracies from MNIST training + optional noise eval (see README). */
export async function fetchOcrAccuracy() {
  const r = await fetch(`${OCR_BASE}/ocr/accuracy`);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(formatHttpError(r.status, data));
  }
  return data;
}

export async function fetchCompressHealth() {
  const r = await fetch(`${COMPRESS_BASE}/health`);
  return r;
}

/** @param {{ referenceText?: string }} [options] optional ground truth for character accuracy */
export async function postOcr(imageFile, options = {}) {
  const fd = new FormData();
  fd.append("image", imageFile);
  const ref = options.referenceText?.trim();
  if (ref) {
    fd.append("reference_text", ref);
  }
  const r = await fetch(`${OCR_BASE}/ocr`, {
    method: "POST",
    body: fd,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(formatHttpError(r.status, data));
  }
  return data;
}

export async function postCompress(text) {
  const r = await fetch(`${COMPRESS_BASE}/compress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(formatHttpError(r.status, data));
  }
  return data;
}

export async function postDecompress(compressed_b64, bwt_index) {
  const r = await fetch(`${COMPRESS_BASE}/decompress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ compressed_b64, bwt_index }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(formatHttpError(r.status, data));
  }
  return data;
}
