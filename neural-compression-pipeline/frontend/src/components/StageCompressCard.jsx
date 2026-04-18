import styles from "./StageCompressCard.module.css";

function formatBytes(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US").format(Math.round(n));
}

export function StageCompressCard({
  headerPillKind,
  headerPillLabel,
  originalSize,
  compressedSize,
  ratio,
  losslessOk,
  diffChars,
  decompressedText,
  onCopyDecompressed,
}) {
  const ratioDisplay =
    typeof ratio === "number" && Number.isFinite(ratio) ? ratio.toFixed(2) : "—";

  return (
    <section className={styles.card}>
      <header className={styles.head}>
        <div className={styles.headLeft}>
          <span className={styles.stageNum}>02</span>
          <span className={styles.stageTitle}>Compress — BWT + Huffman</span>
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
            <div className={styles.statLabel}>Ratio</div>
            <div className={`${styles.statValue} ${styles.ratioVal}`}>
              {ratioDisplay}
              <span className={styles.ratioX}>×</span>
            </div>
          </div>
        </div>

        <div className={styles.badge}>
          <span className={styles.dot} aria-hidden />
          <span className={styles.badgeText}>
            {losslessOk
              ? `Lossless verified — ${diffChars} characters differ`
              : "Lossless check pending"}
          </span>
        </div>

        <div className={styles.decompressBlock}>
          <div className={styles.decompressHead}>
            <span className={styles.sectionLabel}>Decompressed output</span>
            <button type="button" className={styles.copyBtn} onClick={onCopyDecompressed}>
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
          <p className={styles.matchLine}>
            {losslessOk ? "✓ exact match with OCR output" : "Awaiting pipeline run"}
          </p>
        </div>
      </div>
    </section>
  );
}
