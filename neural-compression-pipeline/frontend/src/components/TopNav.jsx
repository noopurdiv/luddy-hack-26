import styles from "./TopNav.module.css";

export function TopNav() {
  return (
    <header className={styles.bar}>
      <div className={styles.left}>
        <span className={styles.logoDot} aria-hidden />
        <span className={styles.brand}>NeuralCompress</span>
      </div>
      <div className={styles.right}>
        <span className={styles.version}>v1.0.0 · hackathon build</span>
      </div>
    </header>
  );
}
