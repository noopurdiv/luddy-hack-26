import { useCallback, useEffect, useState } from "react";

import {
  fetchCompressHealth,
  fetchOcrHealth,
  postCompress,
  postDecompress,
  postOcr,
} from "./api.js";
import styles from "./App.module.css";
import { Connector } from "./components/Connector.jsx";
import { LeftControls } from "./components/LeftControls.jsx";
import { PipelineStatus } from "./components/PipelineStatus.jsx";
import { StageCompressCard } from "./components/StageCompressCard.jsx";
import { StageOcrCard } from "./components/StageOcrCard.jsx";
import { TopNav } from "./components/TopNav.jsx";

/** @typedef {{ kind: 'idle' | 'running' | 'done', label: string }} PipeRow */

function countCharDiff(a, b) {
  const s1 = a ?? "";
  const s2 = b ?? "";
  const len = Math.max(s1.length, s2.length);
  let n = 0;
  for (let i = 0; i < len; i++) {
    if (s1[i] !== s2[i]) n += 1;
  }
  return n;
}

export default function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploadErr, setUploadErr] = useState(null);

  const [processing, setProcessing] = useState(false);
  const [banner, setBanner] = useState(null);

  const [ocrUp, setOcrUp] = useState(true);
  const [compressUp, setCompressUp] = useState(true);

  const [ocrText, setOcrText] = useState("");
  const [confidence, setConfidence] = useState(0);

  const [compressStats, setCompressStats] = useState({
    original_size: null,
    compressed_size: null,
    ratio: null,
    compressed_b64: "",
    bwt_index: 0,
  });

  const [decompressedText, setDecompressedText] = useState("");
  const [losslessOk, setLosslessOk] = useState(false);
  const [diffChars, setDiffChars] = useState(0);

  /** @type {[PipeRow, PipeRow, PipeRow]} */
  const [pipeRows, setPipeRows] = useState([
    { key: "ocr", title: "OCR service", kind: "done", label: "READY" },
    { key: "compress", title: "Compress service", kind: "done", label: "READY" },
    { key: "redis", title: "Redis queue", kind: "done", label: "READY" },
  ]);

  const [stage1Pill, setStage1Pill] = useState({ kind: "idle", label: "READY" });
  const [stage2Pill, setStage2Pill] = useState({ kind: "idle", label: "READY" });

  const refreshHealth = useCallback(async () => {
    let ocrOk = false;
    let cmpOk = false;
    try {
      const r = await fetchOcrHealth();
      const j = await r.json().catch(() => ({}));
      ocrOk = r.ok && j.status === "ok";
    } catch {
      ocrOk = false;
    }
    try {
      const r = await fetchCompressHealth();
      const j = await r.json().catch(() => ({}));
      cmpOk = r.ok && j.status === "ok";
    } catch {
      cmpOk = false;
    }
    setOcrUp(ocrOk);
    setCompressUp(cmpOk);
    if (!ocrOk || !cmpOk) {
      setBanner(
        !ocrOk && !cmpOk
          ? "OCR and compress APIs are unreachable. Start Docker services."
          : !ocrOk
            ? "OCR API unreachable."
            : "Compress API unreachable.",
      );
    } else {
      setBanner(null);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    const id = setInterval(refreshHealth, 30_000);
    return () => clearInterval(id);
  }, [refreshHealth]);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const onFileSelect = useCallback((f, err) => {
    setUploadErr(err);
    setFile(f);
    if (!f) {
      setPreviewUrl(null);
    }
  }, []);

  const resetOutputs = useCallback(() => {
    setOcrText("");
    setConfidence(0);
    setCompressStats({
      original_size: null,
      compressed_size: null,
      ratio: null,
      compressed_b64: "",
      bwt_index: 0,
    });
    setDecompressedText("");
    setLosslessOk(false);
    setDiffChars(0);
  }, []);

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const runPipeline = useCallback(async () => {
    if (!file) return;
    if (!ocrUp || !compressUp) {
      setBanner("Fix service connectivity before running the pipeline.");
      return;
    }

    resetOutputs();
    setProcessing(true);
    setBanner(null);

    setPipeRows([
      { key: "ocr", title: "OCR service", kind: "running", label: "RUNNING" },
      { key: "compress", title: "Compress service", kind: "idle", label: "READY" },
      { key: "redis", title: "Redis queue", kind: "running", label: "RUNNING" },
    ]);
    setStage1Pill({ kind: "running", label: "RUNNING" });
    setStage2Pill({ kind: "idle", label: "READY" });

    try {
      const ocr = await postOcr(file);
      const text = ocr.text ?? "";
      const conf =
        typeof ocr.confidence === "number"
          ? ocr.confidence
          : typeof ocr.confidence === "string"
            ? parseFloat(ocr.confidence)
            : 0;

      setOcrText(text);
      setConfidence(Number.isFinite(conf) ? conf : 0);

      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "done", label: "DONE" },
        { key: "compress", title: "Compress service", kind: "running", label: "RUNNING" },
        { key: "redis", title: "Redis queue", kind: "running", label: "RUNNING" },
      ]);
      setStage1Pill({ kind: "done", label: "DONE" });
      setStage2Pill({ kind: "running", label: "RUNNING" });

      if (!text.trim()) {
        throw new Error("OCR returned empty text — cannot compress.");
      }

      const packed = await postCompress(text);

      setCompressStats({
        original_size: packed.original_size,
        compressed_size: packed.compressed_size,
        ratio: packed.ratio,
        compressed_b64: packed.compressed_b64,
        bwt_index: packed.bwt_index,
      });

      const roundTrip = await postDecompress(packed.compressed_b64, packed.bwt_index);
      const dec = roundTrip.text ?? "";
      setDecompressedText(dec);

      const diff = countCharDiff(text, dec);
      setDiffChars(diff);
      setLosslessOk(diff === 0);

      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "done", label: "DONE" },
        { key: "compress", title: "Compress service", kind: "done", label: "DONE" },
        { key: "redis", title: "Redis queue", kind: "done", label: "DONE" },
      ]);
      setStage2Pill({ kind: "done", label: "DONE" });

      await sleep(900);
      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "done", label: "READY" },
        { key: "compress", title: "Compress service", kind: "done", label: "READY" },
        { key: "redis", title: "Redis queue", kind: "done", label: "READY" },
      ]);
      setStage1Pill({ kind: "idle", label: "READY" });
      setStage2Pill({ kind: "idle", label: "READY" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setBanner(msg);
      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "idle", label: "READY" },
        { key: "compress", title: "Compress service", kind: "idle", label: "READY" },
        { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
      ]);
      setStage1Pill({ kind: "idle", label: "READY" });
      setStage2Pill({ kind: "idle", label: "READY" });
    } finally {
      setProcessing(false);
    }
  }, [file, ocrUp, compressUp, resetOutputs]);

  const onCopyDecompressed = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(decompressedText);
    } catch {
      setBanner("Clipboard permission denied.");
    }
  }, [decompressedText]);

  return (
    <div className={styles.shell}>
      <TopNav />
      <div className={styles.body}>
        <aside className={styles.left}>
          <LeftControls
            file={file}
            previewUrl={previewUrl}
            disabled={!ocrUp || !compressUp}
            processing={processing}
            errorHint={uploadErr}
            onFileSelect={onFileSelect}
            onRun={runPipeline}
          />
          <PipelineStatus rows={pipeRows} />
        </aside>

        <main className={styles.right}>
          {banner ? (
            <div className={styles.banner} role="status">
              {banner}
            </div>
          ) : null}

          <div className={styles.rightInner}>
            <StageOcrCard
              headerPillKind={stage1Pill.kind}
              headerPillLabel={stage1Pill.label}
              text={ocrText}
              confidence={confidence}
            />

            <Connector />

            <StageCompressCard
              headerPillKind={stage2Pill.kind}
              headerPillLabel={stage2Pill.label}
              originalSize={compressStats.original_size}
              compressedSize={compressStats.compressed_size}
              ratio={compressStats.ratio}
              losslessOk={losslessOk}
              diffChars={diffChars}
              decompressedText={decompressedText}
              onCopyDecompressed={onCopyDecompressed}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
