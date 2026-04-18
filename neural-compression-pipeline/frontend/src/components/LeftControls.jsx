import { useCallback, useRef } from "react";

import styles from "./LeftControls.module.css";

const MAX_BYTES = 10 * 1024 * 1024;

export function LeftControls({
  file,
  previewUrl,
  disabled,
  processing,
  errorHint,
  onFileSelect,
  onRun,
}) {
  const inputRef = useRef(null);

  const validateAndSet = useCallback(
    (f) => {
      if (!f) return;
      if (!["image/png", "image/jpeg"].includes(f.type)) {
        onFileSelect(null, "Use PNG or JPEG.");
        return;
      }
      if (f.size > MAX_BYTES) {
        onFileSelect(null, "Max file size is 10MB.");
        return;
      }
      onFileSelect(f, null);
    },
    [onFileSelect],
  );

  const onChange = (e) => {
    const f = e.target.files?.[0];
    validateAndSet(f);
    e.target.value = "";
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const f = e.dataTransfer.files?.[0];
    validateAndSet(f);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  return (
    <div className={styles.stack}>
      <div
        className={styles.dropzone}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg"
          className={styles.hiddenInput}
          onChange={onChange}
        />
        <div className={styles.iconBox} aria-hidden>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 5v14M8 9l4-4 4 4"
              stroke="#555"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <p className={styles.dropTitle}>Drop a scanned document</p>
        <p className={styles.dropHint}>PNG or JPEG · max 10MB</p>
      </div>

      <div className={styles.preview}>
        {previewUrl ? (
          <img src={previewUrl} alt="Document preview" className={styles.previewImg} />
        ) : (
          <span className={styles.previewEmpty}>no image loaded</span>
        )}
      </div>

      {errorHint ? <p className={styles.fieldError}>{errorHint}</p> : null}

      <button
        type="button"
        className={styles.runBtn}
        disabled={disabled || !file || processing}
        onClick={onRun}
      >
        {processing ? "Processing…" : "Run pipeline"}
      </button>
    </div>
  );
}
