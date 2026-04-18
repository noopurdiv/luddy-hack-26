import styles from "./StageCompressCard.module.css";

function formatBytes(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US").format(Math.round(n));
}

function formatMetric(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return n.toFixed(4);
}

export function StageCompressCard({
  headerPillKind,
  headerPillLabel,
  originalSize,
  compressedSize,
  compressionRate,
  entropyBitsPerSymbol,
  avgHuffmanBitsPerSymbol,
  encodingEfficiency,
  losslessOk,
  diffChars,
  decompressedText,
  onCopyDecompressed,
  hasCompressed = false,
  hasDecompressed = false,
  onDownloadCompressedBundle,
  onDownloadDecompressedFile,
}) {
  const rateDisplay =
    typeof compressionRate === "number" && Number.isFinite(compressionRate)
      ? compressionRate.toFixed(1)
      : "—";

  let losslessBadgeText = "Run Decompress to verify a lossless round-trip";
  if (losslessOk === true) {
    losslessBadgeText = "Lossless verified — decompressed text matches the original exactly";
  } else if (losslessOk === false) {
    losslessBadgeText = `Mismatch — ${diffChars} character positions differ from the original`;
  } else if (!hasCompressed) {
    losslessBadgeText = "Compress an image to produce a bundle, then run Decompress";
  }

  let matchLine = "Awaiting Decompress";
  if (losslessOk === true) {
    matchLine = "✓ Exact match with the text that was compressed (byte-for-byte)";
  } else if (losslessOk === false) {
    matchLine = "✗ Output does not match the original compressed string";
  }

  return (
    <section className={styles.card}>
      <header className={styles.head}>
        <div className={styles.headLeft}>
          <span className={styles.stageNum}>02</span>
          <span className={styles.stageTitle}>Compress — BWT + MTF + Huffman</span>
        </div>
        <span
          className={`${styles.statusPill} ${
            headerPillKind === "running"
              ? styles.spRunning
              : headerPillKind === "done"
                ? styles.spDone
                : styles.spIdle
          }`}
        >
          {headerPillLabel}
        </span>
      </header>

      <div className={styles.body}>
        <div className={styles.stats}>
          <div className={styles.stat}>
            <div className={styles.statLabel}>Original</div>
            <div className={styles.statValue}>
              {formatBytes(originalSize)}
              <span className={styles.unit}>B</span>
            </div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statLabel}>Compressed</div>
            <div className={styles.statValue}>
              {formatBytes(compressedSize)}
              <span className={styles.unit}>B</span>
            </div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statLabel}>Compression Rate</div>
            <div className={`${styles.statValue} ${styles.ratioVal}`}>
              {rateDisplay}
              <span className={styles.ratioX}>%</span>
            </div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statLabel}>Entropy (bits / symbol)</div>
            <div className={styles.statValue}>{formatMetric(entropyBitsPerSymbol)}</div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statLabel}>Avg Huffman bits / symbol</div>
            <div className={styles.statValue}>{formatMetric(avgHuffmanBitsPerSymbol)}</div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statLabel}>Encoding efficiency</div>
            <div className={styles.statValue}>{formatMetric(encodingEfficiency)}</div>
          </div>
        </div>

        <div className={styles.fileActions}>
          <button
            type="button"
            className={styles.fileBtn}
            disabled={!hasCompressed}
            onClick={onDownloadCompressedBundle}
          >
            Download compressed bundle
          </button>
          <button
            type="button"
            className={styles.fileBtn}
            disabled={!hasDecompressed}
            onClick={onDownloadDecompressedFile}
          >
            Download decompressed file
          </button>
        </div>

        <div className={styles.badge}>
          <span className={styles.dot} aria-hidden />
          <span className={styles.badgeText}>{losslessBadgeText}</span>
        </div>

        <div className={styles.decompressBlock}>
          <div className={styles.decompressHead}>
            <span className={styles.sectionLabel}>Decompressed output</span>
            <button
              type="button"
              className={styles.copyBtn}
              disabled={!hasDecompressed}
              onClick={onCopyDecompressed}
            >
              copy
            </button>
          </div>
          <textarea
            className={styles.ta}
            readOnly
            value={decompressedText}
            placeholder="Round-trip text appears here…"
            rows={5}
          />
          <p
            className={`${styles.matchLine} ${losslessOk === false ? styles.matchLineBad : ""}`}
          >
            {matchLine}
          </p>
        </div>
      </div>
    </section>
  );
}
