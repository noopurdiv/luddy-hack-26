import styles from "./Connector.module.css";

export function Connector() {
  return (
    <div className={styles.wrap} aria-hidden="true">
      <span className={styles.line} />
      <span className={styles.label}>BWT → HUFFMAN ENCODER</span>
      <span className={styles.line} />
    </div>
  );
}
