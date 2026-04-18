import styles from "./PipelineStatus.module.css";

/** @typedef {'idle' | 'running' | 'done'} PillKind */

function Pill({ kind, label }) {
  const cls =
    kind === "running"
      ? styles.pillRunning
      : kind === "done"
        ? styles.pillDone
        : styles.pillIdle;

  return (
    <span className={`${styles.pill} ${cls}`} role="status">
      {label}
    </span>
  );
}

export function PipelineStatus({ rows }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionLabel}>Pipeline status</div>
      <div className={styles.list}>
        {rows.map((row) => (
          <div key={row.key} className={styles.row}>
            <span className={styles.rowLabel}>{row.title}</span>
            <Pill kind={row.kind} label={row.label} />
          </div>
        ))}
      </div>
    </section>
  );
}
