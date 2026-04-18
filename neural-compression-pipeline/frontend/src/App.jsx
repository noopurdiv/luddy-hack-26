import { useCallback, useEffect, useState } from "react";
import {
  fetchCompressHealth, fetchOcrHealth,
  postCompress, postDecompress, postOcr,
} from "./api.js";
import { downloadString } from "./download.js";
import styles from "./App.module.css";
import { UploadView } from "./components/UploadView.jsx";
import { ResultView } from "./components/ResultView.jsx";
import { VerifyView } from "./components/VerifyView.jsx";
import { ProcessingView } from "./components/ProcessingView.jsx";

const emptyCompressStats = () => ({
  original_size: null, compressed_size: null, compression_rate: null,
  compressed_b64: "", bwt_index: 0, entropy_bits_per_symbol: null,
  avg_huffman_bits_per_symbol: null, encoding_efficiency: null,
});

function countCharDiff(a, b) {
  const s1 = a ?? "", s2 = b ?? "";
  const len = Math.max(s1.length, s2.length);
  let n = 0;
  for (let i = 0; i < len; i++) if (s1[i] !== s2[i]) n++;
  return n;
}

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "grid" },
  { key: "processor", label: "Processor", icon: "cpu", active: true },
  { key: "archives", label: "Archives", icon: "archive" },
  { key: "templates", label: "Templates", icon: "layers" },
  { key: "settings", label: "Settings", icon: "settings" },
];

function NavIcon({ name }) {
  const icons = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    cpu: <><rect x="9" y="9" width="6" height="6" rx="1"/><rect x="2" y="2" width="20" height="20" rx="3" fill="none" stroke="currentColor" strokeWidth="2"/><line x1="9" y1="2" x2="9" y2="5"/><line x1="15" y1="2" x2="15" y2="5"/><line x1="9" y1="19" x2="9" y2="22"/><line x1="15" y1="19" x2="15" y2="22"/><line x1="2" y1="9" x2="5" y2="9"/><line x1="2" y1="15" x2="5" y2="15"/><line x1="19" y1="9" x2="22" y2="9"/><line x1="19" y1="15" x2="22" y2="15"/></>,
    archive: <><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5" rx="1"/><line x1="10" y1="12" x2="14" y2="12"/></>,
    layers: <><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
  };
  return (
    <svg className={styles.navIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {icons[name]}
    </svg>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState("");
  const [banner, setBanner] = useState(null);
  const [ocrUp, setOcrUp] = useState(true);
  const [compressUp, setCompressUp] = useState(true);
  const [ocrText, setOcrText] = useState("");
  const [confidence, setConfidence] = useState(0);
  const [ocrBackend, setOcrBackend] = useState(null);
  const [compressStats, setCompressStats] = useState(emptyCompressStats);
  const [originalPlaintext, setOriginalPlaintext] = useState("");
  const [decompressedText, setDecompressedText] = useState("");
  const [losslessOk, setLosslessOk] = useState(null);
  const [diffChars, setDiffChars] = useState(0);
  const [processingTime, setProcessingTime] = useState(null);
  const [activeNav, setActiveNav] = useState("processor");

  const isDone = Boolean(ocrText || compressStats.compressed_b64);
  const isVerified = losslessOk !== null;

  const view = processing ? "processing"
    : isVerified ? "verification"
    : isDone ? "result"
    : "upload";

  const refreshHealth = useCallback(async () => {
    let ocrOk = false, cmpOk = false;
    try { const r = await fetchOcrHealth(); const j = await r.json().catch(() => ({})); ocrOk = r.ok && j.status === "ok"; } catch {}
    try { const r = await fetchCompressHealth(); const j = await r.json().catch(() => ({})); cmpOk = r.ok && j.status === "ok"; } catch {}
    setOcrUp(ocrOk); setCompressUp(cmpOk);
    if (!ocrOk || !cmpOk) {
      setBanner(!ocrOk && !cmpOk ? "OCR and compress APIs are unreachable. Start Docker services." : !ocrOk ? "OCR API unreachable." : "Compress API unreachable.");
    } else { setBanner(null); }
  }, []);

  useEffect(() => {
    refreshHealth();
    const id = setInterval(refreshHealth, 30_000);
    return () => clearInterval(id);
  }, [refreshHealth]);

  useEffect(() => {
    if (!file) { setPreviewUrl(null); return; }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const resetAll = useCallback(() => {
    setOcrText(""); setConfidence(0); setOcrBackend(null);
    setCompressStats(emptyCompressStats());
    setOriginalPlaintext(""); setDecompressedText("");
    setLosslessOk(null); setDiffChars(0); setProcessingTime(null);
  }, []);

  const onFileSelect = useCallback((f, err) => {
    setBanner(err || null);
    resetAll();
    setFile(f);
  }, [resetAll]);

  const onNewDocument = useCallback(() => {
    resetAll();
    setFile(null);
    setPreviewUrl(null);
    setBanner(null);
  }, [resetAll]);

  const onCompress = useCallback(async () => {
    if (!file) return;
    if (!ocrUp || !compressUp) { setBanner("Fix service connectivity first."); return; }
    setBanner(null);
    setProcessing(true);
    setProcessingStage("Extracting text with Neural OCR…");
    setDecompressedText(""); setLosslessOk(null); setDiffChars(0);
    const t0 = Date.now();
    try {
      const ocr = await postOcr(file);
      const text = ocr.text ?? "";
      const conf = typeof ocr.confidence === "number" ? ocr.confidence : parseFloat(ocr.confidence) || 0;
      setOcrBackend(typeof ocr.ocr_backend === "string" ? ocr.ocr_backend : null);
      setOcrText(text); setConfidence(Number.isFinite(conf) ? conf : 0);
      if (!text.trim()) { setBanner("No text detected in the image."); return; }
      setProcessingStage("Compressing with Adaptive Huffman…");
      const packed = await postCompress(text);
      setOriginalPlaintext(text);
      setCompressStats({
        original_size: packed.original_size, compressed_size: packed.compressed_size,
        compression_rate: packed.compression_rate, compressed_b64: packed.compressed_b64,
        bwt_index: packed.bwt_index,
        entropy_bits_per_symbol: packed.entropy_bits_per_symbol ?? null,
        avg_huffman_bits_per_symbol: packed.avg_huffman_bits_per_symbol ?? null,
        encoding_efficiency: packed.encoding_efficiency ?? null,
      });
      setProcessingTime(((Date.now() - t0) / 1000).toFixed(1));
      downloadString("compressed-bundle.json", JSON.stringify({ version: 1, compressed_b64: packed.compressed_b64, bwt_index: packed.bwt_index, original_size: packed.original_size, compressed_size: packed.compressed_size, compression_rate: packed.compression_rate, entropy_bits_per_symbol: packed.entropy_bits_per_symbol, avg_huffman_bits_per_symbol: packed.avg_huffman_bits_per_symbol, encoding_efficiency: packed.encoding_efficiency }, null, 2), "application/json");
    } catch (e) {
      setBanner(e instanceof Error ? e.message : String(e));
      setCompressStats(emptyCompressStats());
    } finally {
      setProcessing(false); setProcessingStage("");
    }
  }, [file, ocrUp, compressUp]);

  const onDecompress = useCallback(async () => {
    if (!compressStats.compressed_b64 || !originalPlaintext) { setBanner("Compress first."); return; }
    setBanner(null); setProcessing(true); setProcessingStage("Verifying lossless round-trip…");
    try {
      const roundTrip = await postDecompress(compressStats.compressed_b64, compressStats.bwt_index);
      const dec = roundTrip.text ?? "";
      setDecompressedText(dec);
      const match = dec === originalPlaintext;
      setLosslessOk(match);
      setDiffChars(match ? 0 : countCharDiff(originalPlaintext, dec));
      downloadString(match ? "decompressed.txt" : "decompressed-output.txt", dec, "text/plain;charset=utf-8");
    } catch (e) {
      setBanner(e instanceof Error ? e.message : String(e));
    } finally {
      setProcessing(false); setProcessingStage("");
    }
  }, [compressStats, originalPlaintext]);

  const onDownloadBundle = useCallback(() => {
    if (!compressStats.compressed_b64) return;
    downloadString("compressed-bundle.json", JSON.stringify({ version: 1, ...compressStats }, null, 2), "application/json");
  }, [compressStats]);

  const onDownloadDecompressed = useCallback(() => {
    if (!decompressedText) return;
    downloadString(losslessOk ? "decompressed.txt" : "decompressed-output.txt", decompressedText, "text/plain;charset=utf-8");
  }, [decompressedText, losslessOk]);

  const filename = file?.name ?? "document";

  return (
    <div className={styles.shell}>
      {/* ── Sidebar ── */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarBrand}>
          <div className={styles.brandLogo}>
            <div className={styles.brandIcon}><div className={styles.brandIconInner}/></div>
            <span className={styles.brandName}>Processor Pro</span>
          </div>
          <div className={styles.brandSub}>Technical Purist v1.0</div>
        </div>
        <nav className={styles.sidebarNav}>
          {NAV_ITEMS.map(item => (
            <button
              key={item.key}
              className={`${styles.navItem} ${activeNav === item.key ? styles.navItemActive : ""}`}
              onClick={() => setActiveNav(item.key)}
            >
              <NavIcon name={item.icon} />
              {item.label}
            </button>
          ))}
        </nav>
        <div className={styles.sidebarFooter}>
          <button className={styles.newDocBtn} onClick={onNewDocument}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            New Document
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className={styles.main}>
        <header className={styles.topBar}>
          <span className={styles.topBarBrand}>DocPurist</span>
          {view === "result" && (
            <div className={styles.topBarTabs}>
              <span className={`${styles.topBarTab} ${styles.topBarTabActive}`}>Files</span>
              <span className={styles.topBarTab}>Queue</span>
              <span className={styles.topBarTab}>Networks</span>
            </div>
          )}
          <div className={styles.topBarActions}>
            <button className={styles.topBarIconBtn} title="Notifications">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            </button>
            <button className={styles.topBarIconBtn} title="Settings">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/></svg>
            </button>
            <div className={styles.topBarAvatar}>PP</div>
          </div>
        </header>

        <div className={styles.content}>
          {banner && <div className={`${styles.banner} ${banner.includes("unreachable") ? styles.bannerErr : ""}`}>{banner}</div>}

          {view === "processing" && <ProcessingView stage={processingStage} filename={filename} />}
          {view === "upload" && (
            <UploadView
              file={file} previewUrl={previewUrl}
              disabled={!ocrUp || !compressUp}
              onFileSelect={onFileSelect} onCompress={onCompress}
              ocrUp={ocrUp} compressUp={compressUp}
            />
          )}
          {view === "result" && (
            <ResultView
              filename={filename} previewUrl={previewUrl}
              ocrText={ocrText} confidence={confidence}
              ocrBackend={ocrBackend} processingTime={processingTime}
              compressStats={compressStats}
              onDecompress={onDecompress}
              onDownloadBundle={onDownloadBundle}
              canDecompress={Boolean(compressStats.compressed_b64)}
            />
          )}
          {view === "verification" && (
            <VerifyView
              losslessOk={losslessOk} diffChars={diffChars}
              decompressedText={decompressedText}
              compressStats={compressStats}
              onDownloadBundle={onDownloadBundle}
              onDownloadDecompressed={onDownloadDecompressed}
              onReset={onNewDocument}
            />
          )}
        </div>
      </div>
    </div>
  );
}
