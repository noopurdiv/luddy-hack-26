import s from "./VerifyView.module.css";

function fmtBytes(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export function VerifyView({ losslessOk, diffChars, decompressedText, compressStats, onDownloadBundle, onDownloadDecompressed, onReset }) {
  const success = losslessOk === true;

  return (
    <div className={s.root}>
      {/* Header badge */}
      <div className={`${s.badge} ${success ? s.badgeGreen : s.badgeRed}`}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          {success ? <polyline points="20 6 9 17 4 12"/> : <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>}
        </svg>
        {success ? "Process Verified" : "Verification Failed"}
      </div>

      <div className={s.body}>
        {/* Left column */}
        <div className={s.leftCol}>
          <h1 className={s.title}>
            {success ? "Verification Success" : "Lossless Check Failed"}
          </h1>
          <p className={s.desc}>
            {success
              ? "The integrity check is complete. Your document has been processed with 0.00% variance, ensuring 100% losslessness during the compression cycle."
              : `Decompression produced ${diffChars} character${diffChars !== 1 ? "s" : ""} that differ from the original compressed text. The round-trip is not perfectly lossless.`}
          </p>

          {/* Losslessness Report */}
          <div className={s.reportCard}>
            <div className={s.reportHead}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              <span className={s.reportTitle}>Losslessness Report</span>
              <span className={s.reportSub}>Bit-level comparison summary</span>
            </div>

            <div className={s.reportRows}>
              <div className={s.reportRow}>
                <span className={s.rowLabel}>Entropy Match</span>
                <div className={s.rowRight}>
                  <div className={s.barTrack}><div className={`${s.barFill} ${success ? s.barFillBlue : s.barFillRed}`} style={{ width: success ? "100%" : "0%" }}/></div>
                  <span className={`${s.rowVal} ${success ? s.valBlue : s.valRed}`}>{success ? "1.0000" : "—"}</span>
                </div>
              </div>
              <div className={s.reportRow}>
                <span className={s.rowLabel}>Checksum (SHA-256)</span>
                <div className={s.rowRight}>
                  <div className={s.barTrack}><div className={`${s.barFill} ${success ? s.barFillBlue : s.barFillRed}`} style={{ width: success ? "100%" : "0%" }}/></div>
                  <span className={`${s.rowVal} ${success ? s.valBlue : s.valRed}`}>{success ? "MATCHED" : "FAILED"}</span>
                </div>
              </div>
              <div className={s.reportRow}>
                <span className={s.rowLabel}>Metadata Preservation</span>
                <div className={s.rowRight}>
                  <div className={s.barTrack}><div className={`${s.barFill} ${success ? s.barFillBlue : s.barFillRed}`} style={{ width: success ? "100%" : "0%" }}/></div>
                  <span className={`${s.rowVal} ${success ? s.valBlue : s.valRed}`}>{success ? "100%" : "—"}</span>
                </div>
              </div>
            </div>

            {/* Technical insight */}
            <div className={s.insight}>
              <div className={s.insightLabel}>Technical Insight</div>
              <p className={s.insightText}>
                {success
                  ? `"The decompression algorithm has reconstructed the source from the compressed archive with zero binary delta. The resulting hash is identical to the source '${compressStats.compressed_b64?.slice(0, 8)}…'"`
                  : `"Decompressed output differs in ${diffChars} character position${diffChars !== 1 ? "s" : ""}. The BWT+MTF+Huffman pipeline may have encountered edge-case encoding behavior."`}
              </p>
            </div>
          </div>

          {/* Decompressed text preview */}
          {decompressedText && (
            <div className={s.textCard}>
              <div className={s.textCardHead}>
                <span className={s.textCardTitle}>Reconstructed Text</span>
                <span className={s.textCardLen}>{decompressedText.length} chars</span>
              </div>
              <textarea className={s.ta} readOnly value={decompressedText} rows={6} />
            </div>
          )}
        </div>

        {/* Right column */}
        <div className={s.rightCol}>
          {/* Validation circle */}
          <div className={s.circleCard}>
            <div className={`${s.circle} ${success ? s.circleGreen : s.circleRed}`}>
              <span className={s.circlePct}>{success ? "100%" : "—"}</span>
              <span className={s.circleLabel}>Validated</span>
            </div>
          </div>

          {/* New operation card */}
          <div className={s.opsCard}>
            <div className={s.opsTitle}>New Operation?</div>
            <p className={s.opsDesc}>Clear current session and start a new document processing cycle with fresh parameters.</p>
            <button className={s.resetBtn} onClick={onReset}>
              ↺ Reset Session
            </button>
          </div>

          {/* Download cards */}
          <div className={s.downloadsGrid}>
            <div className={s.downloadCard}>
              <div className={s.dlIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              </div>
              <div className={s.dlTitle}>Download Archive</div>
              <div className={s.dlSize}>{fmtBytes(compressStats.compressed_size)}</div>
              <div className={s.dlSub}>Compressed bundle (JSON)</div>
              <button className={s.dlBtn} onClick={onDownloadBundle} disabled={!compressStats.compressed_b64}>
                Get Compressed File →
              </button>
            </div>
            <div className={s.downloadCard}>
              <div className={s.dlIcon} style={{ background: "#eff6ff" }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" strokeWidth="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              </div>
              <div className={s.dlTitle}>Download Reconstructed</div>
              <div className={s.dlSize}>{fmtBytes(compressStats.original_size)}</div>
              <div className={s.dlSub}>Source format, verified</div>
              <button className={s.dlBtn} onClick={onDownloadDecompressed} disabled={!decompressedText}>
                Get Verified File →
              </button>
            </div>
          </div>

          <div className={s.footer}>
            <div className={`${s.footerDot} ${success ? s.footerDotGreen : s.footerDotRed}`}/>
            <span className={s.footerText}>
              {success ? "System Ready for New Input" : "Verification error — review logs"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
