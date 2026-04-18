import styles from "./StageOcrCard.module.css";

export function StageOcrCard({ headerPillKind, headerPillLabel, text, confidence }) {
  const pct =
    typeof confidence === "number" && Number.isFinite(confidence)
      ? Math.round(Math.min(1, Math.max(0, confidence)) * 1000) / 10
      : 0;
  const fillWidth = `${pct}%`;

  return (
    <section className={styles.card}>
      <header className={styles.head}>
        <div className={styles.headLeft}>
          <span className={styles.stageNum}>01</span>
          <span className={styles.stageTitle}>OCR — SimpleHTR CNN</span>
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
        <textarea
          className={styles.ta}
          readOnly
          value={text}
          placeholder="OCR output will appear here…"
          rows={5}
        />
        <div className={styles.confRow}>
          <span className={styles.confLabel}>CONFIDENCE</span>
          <div className={styles.barTrack}>
            <div className={styles.barFill} style={{ width: fillWidth }} />
          </div>
          <span className={styles.confVal}>{pct.toFixed(1)}%</span>
        </div>
      </div>
    </section>
  );
}
