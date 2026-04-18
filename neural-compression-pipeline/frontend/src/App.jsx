import { useCallback, useEffect, useState } from "react";

import {
  fetchCompressHealth,
  fetchOcrHealth,
  postCompress,
  postDecompress,
  postOcr,
} from "./api.js";
import { downloadString } from "./download.js";
import styles from "./App.module.css";
import { Connector } from "./components/Connector.jsx";
import { LeftControls } from "./components/LeftControls.jsx";
import { PipelineStatus } from "./components/PipelineStatus.jsx";
import { StageCompressCard } from "./components/StageCompressCard.jsx";
import { StageOcrCard } from "./components/StageOcrCard.jsx";
import { TopNav } from "./components/TopNav.jsx";

/** @typedef {{ kind: 'idle' | 'running' | 'done', label: string }} PipeRow */

const NO_TEXT_IN_IMAGE = "No text detected in the image";

const IDLE_PIPE_ROWS = [
  { key: "ocr", title: "OCR service", kind: "idle", label: "READY" },
  { key: "compress", title: "Compress service", kind: "idle", label: "READY" },
  { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
];

const emptyCompressStats = () => ({
  original_size: null,
  compressed_size: null,
  compression_rate: null,
  compressed_b64: "",
  bwt_index: 0,
  entropy_bits_per_symbol: null,
  avg_huffman_bits_per_symbol: null,
  encoding_efficiency: null,
});

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
  /** @type {null | 'compress' | 'decompress'} */
  const [processingKind, setProcessingKind] = useState(null);
  const [banner, setBanner] = useState(null);

  const [ocrUp, setOcrUp] = useState(true);
  const [compressUp, setCompressUp] = useState(true);

  const [ocrText, setOcrText] = useState("");
  const [confidence, setConfidence] = useState(0);
  /** From last POST /ocr — pipeline-reported metrics (see service_ocr inference). */
  const [ocrBackend, setOcrBackend] = useState(null);
  const [pipelineMnistValAcc, setPipelineMnistValAcc] = useState(null);
  const [charAccuracyVsReference, setCharAccuracyVsReference] = useState(null);

  const [compressStats, setCompressStats] = useState(() => emptyCompressStats());

  /** Plain string that was sent to /compress — decompressed output must match exactly. */
  const [originalPlaintext, setOriginalPlaintext] = useState("");

  const [decompressedText, setDecompressedText] = useState("");
  /** @type {null | boolean} */
  const [losslessOk, setLosslessOk] = useState(null);
  const [diffChars, setDiffChars] = useState(0);

  /** @type {[PipeRow, PipeRow, PipeRow]} */
  const [pipeRows, setPipeRows] = useState(IDLE_PIPE_ROWS);

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

  const resetOutputs = useCallback(() => {
    setOcrText("");
    setConfidence(0);
    setOcrBackend(null);
    setPipelineMnistValAcc(null);
    setCharAccuracyVsReference(null);
    setCompressStats(emptyCompressStats());
    setOriginalPlaintext("");
    setDecompressedText("");
    setLosslessOk(null);
    setDiffChars(0);
  }, []);

  const onFileSelect = useCallback(
    (f, err) => {
      setUploadErr(err);
      resetOutputs();
      setFile(f);
      if (!f) {
        setPreviewUrl(null);
      }
    },
    [resetOutputs],
  );

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const canDecompress = Boolean(compressStats.compressed_b64?.length);

  const onCompress = useCallback(async () => {
    if (!file) return;
    if (!ocrUp || !compressUp) {
      setBanner("Fix service connectivity before running the pipeline.");
      return;
    }

    setBanner(null);
    setProcessingKind("compress");
    setProcessing(true);
    setDecompressedText("");
    setLosslessOk(null);
    setDiffChars(0);

    setPipeRows([
      { key: "ocr", title: "OCR service", kind: "running", label: "RUNNING" },
      { key: "compress", title: "Compress service", kind: "idle", label: "READY" },
      { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
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

      setOcrBackend(typeof ocr.ocr_backend === "string" ? ocr.ocr_backend : null);
      setPipelineMnistValAcc(
        typeof ocr.mnist_validation_accuracy_recorded === "number"
          ? ocr.mnist_validation_accuracy_recorded
          : null,
      );
      setCharAccuracyVsReference(
        typeof ocr.character_accuracy_vs_reference === "number"
          ? ocr.character_accuracy_vs_reference
          : null,
      );

      setOcrText(text);
      setConfidence(Number.isFinite(conf) ? conf : 0);

      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "done", label: "DONE" },
        { key: "compress", title: "Compress service", kind: "running", label: "RUNNING" },
        { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
      ]);
      setStage1Pill({ kind: "done", label: "DONE" });
      setStage2Pill({ kind: "running", label: "RUNNING" });

      if (!text.trim()) {
        setBanner(NO_TEXT_IN_IMAGE);
        setOriginalPlaintext("");
        setCompressStats(emptyCompressStats());
        setStage2Pill({ kind: "idle", label: "READY" });
        setPipeRows(IDLE_PIPE_ROWS);
        setStage1Pill({ kind: "idle", label: "READY" });
        return;
      }

      const packed = await postCompress(text);

      setOriginalPlaintext(text);
      setCompressStats({
        original_size: packed.original_size,
        compressed_size: packed.compressed_size,
        compression_rate: packed.compression_rate,
        compressed_b64: packed.compressed_b64,
        bwt_index: packed.bwt_index,
        entropy_bits_per_symbol: packed.entropy_bits_per_symbol ?? null,
        avg_huffman_bits_per_symbol: packed.avg_huffman_bits_per_symbol ?? null,
        encoding_efficiency: packed.encoding_efficiency ?? null,
      });

      downloadString(
        "compressed-bundle.json",
        JSON.stringify(
          {
            version: 1,
            compressed_b64: packed.compressed_b64,
            bwt_index: packed.bwt_index,
            original_size: packed.original_size,
            compressed_size: packed.compressed_size,
            compression_rate: packed.compression_rate,
            entropy_bits_per_symbol: packed.entropy_bits_per_symbol,
            avg_huffman_bits_per_symbol: packed.avg_huffman_bits_per_symbol,
            encoding_efficiency: packed.encoding_efficiency,
          },
          null,
          2,
        ),
        "application/json",
      );

      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "done", label: "DONE" },
        { key: "compress", title: "Compress service", kind: "done", label: "DONE" },
        { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
      ]);
      setStage2Pill({ kind: "done", label: "DONE" });

      await sleep(500);
      setPipeRows(IDLE_PIPE_ROWS);
      setStage1Pill({ kind: "idle", label: "READY" });
      setStage2Pill({ kind: "idle", label: "READY" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setBanner(msg);
      setCompressStats(emptyCompressStats());
      setOriginalPlaintext("");
      setPipeRows(IDLE_PIPE_ROWS);
      setStage1Pill({ kind: "idle", label: "READY" });
      setStage2Pill({ kind: "idle", label: "READY" });
    } finally {
      setProcessing(false);
      setProcessingKind(null);
    }
  }, [file, ocrUp, compressUp]);

  const onDecompress = useCallback(async () => {
    if (!compressStats.compressed_b64) {
      setBanner("Compress the image first.");
      return;
    }
    if (!originalPlaintext) {
      setBanner("Compress the image first.");
      return;
    }
    if (!ocrUp || !compressUp) {
      setBanner("Fix service connectivity before running the pipeline.");
      return;
    }

    setBanner(null);
    setProcessingKind("decompress");
    setProcessing(true);
    setLosslessOk(null);
    setDecompressedText("");
    setDiffChars(0);

    setPipeRows([
      {
        key: "ocr",
        title: "OCR service",
        kind: "done",
        label: "DONE",
      },
      { key: "compress", title: "Compress service", kind: "running", label: "RUNNING" },
      { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
    ]);
    setStage2Pill({ kind: "running", label: "RUNNING" });

    try {
      const roundTrip = await postDecompress(
        compressStats.compressed_b64,
        compressStats.bwt_index,
      );
      const dec = roundTrip.text ?? "";
      setDecompressedText(dec);

      const match = dec === originalPlaintext;
      setLosslessOk(match);
      setDiffChars(match ? 0 : countCharDiff(originalPlaintext, dec));

      downloadString(
        match ? "decompressed.txt" : "decompressed-output.txt",
        dec,
        "text/plain;charset=utf-8",
      );

      if (!match) {
        setBanner(
          "Decompressed text does not match the original. Lossless round-trip failed.",
        );
      }

      setPipeRows([
        { key: "ocr", title: "OCR service", kind: "done", label: "DONE" },
        { key: "compress", title: "Compress service", kind: "done", label: "DONE" },
        { key: "redis", title: "Redis queue", kind: "idle", label: "READY" },
      ]);
      setStage2Pill({ kind: "done", label: "DONE" });

      await sleep(400);
      setPipeRows(IDLE_PIPE_ROWS);
      setStage2Pill({ kind: "idle", label: "READY" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setBanner(msg);
      setPipeRows(IDLE_PIPE_ROWS);
      setStage2Pill({ kind: "idle", label: "READY" });
    } finally {
      setProcessing(false);
      setProcessingKind(null);
    }
  }, [compressStats, originalPlaintext, ocrUp, compressUp]);

  const onCopyDecompressed = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(decompressedText);
    } catch {
      setBanner("Clipboard permission denied.");
    }
  }, [decompressedText]);

  const onDownloadCompressedBundle = useCallback(() => {
    if (!compressStats.compressed_b64) return;
    downloadString(
      "compressed-bundle.json",
      JSON.stringify(
        {
          version: 1,
          compressed_b64: compressStats.compressed_b64,
          bwt_index: compressStats.bwt_index,
          original_size: compressStats.original_size,
          compressed_size: compressStats.compressed_size,
          compression_rate: compressStats.compression_rate,
          entropy_bits_per_symbol: compressStats.entropy_bits_per_symbol,
          avg_huffman_bits_per_symbol: compressStats.avg_huffman_bits_per_symbol,
          encoding_efficiency: compressStats.encoding_efficiency,
        },
        null,
        2,
      ),
      "application/json",
    );
  }, [compressStats]);

  const onDownloadDecompressedFile = useCallback(() => {
    if (!decompressedText) return;
    const ok = losslessOk === true;
    downloadString(
      ok ? "decompressed.txt" : "decompressed-output.txt",
      decompressedText,
      "text/plain;charset=utf-8",
    );
  }, [decompressedText, losslessOk]);

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
            processingKind={processing ? processingKind : null}
            canDecompress={canDecompress}
            errorHint={uploadErr}
            onFileSelect={onFileSelect}
            onCompress={onCompress}
            onDecompress={onDecompress}
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
              ocrBackend={ocrBackend}
              pipelineMnistValAcc={pipelineMnistValAcc}
              charAccuracyVsReference={charAccuracyVsReference}
            />

            <Connector />

            <StageCompressCard
              headerPillKind={stage2Pill.kind}
              headerPillLabel={stage2Pill.label}
              originalSize={compressStats.original_size}
              compressedSize={compressStats.compressed_size}
              compressionRate={compressStats.compression_rate}
              entropyBitsPerSymbol={compressStats.entropy_bits_per_symbol}
              avgHuffmanBitsPerSymbol={compressStats.avg_huffman_bits_per_symbol}
              encodingEfficiency={compressStats.encoding_efficiency}
              losslessOk={losslessOk}
              diffChars={diffChars}
              decompressedText={decompressedText}
              onCopyDecompressed={onCopyDecompressed}
              hasCompressed={canDecompress}
              hasDecompressed={decompressedText.length > 0}
              onDownloadCompressedBundle={onDownloadCompressedBundle}
              onDownloadDecompressedFile={onDownloadDecompressedFile}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
