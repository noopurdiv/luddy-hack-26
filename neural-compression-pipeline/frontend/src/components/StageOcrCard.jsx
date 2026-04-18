import { useCallback, useEffect, useState } from "react";

import { fetchOcrAccuracy } from "../api.js";
import styles from "./StageOcrCard.module.css";

/** Case rubric: MNIST CNN must reach ≥95% on the held-out validation split for scoring eligibility. */
export const CASE_CHAR_LEVEL_MIN_PCT = 95;

function pctFromRatio(x) {
  if (typeof x !== "number" || !Number.isFinite(x)) return "—";
  const p = x <= 1 ? x * 100 : x;
  return `${p.toFixed(2)}%`;
}

function ratioFromPayload(m) {
  const v = m?.best_validation_accuracy;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function formatBackend(b) {
  if (b === "mnist_cnn") return "MNIST CNN (digit)";
  if (b === "simple_htr") return "SimpleHTR (line)";
  if (b === "tesseract") return "Tesseract (fallback)";
  if (typeof b === "string" && b.trim()) return b;
  return null;
}

function PipelineRunMetrics({ ocrBackend, pipelineMnistValAcc, charAccuracyVsReference }) {
  const engineLabel = formatBackend(ocrBackend);
  const hasRecorded =
    typeof pipelineMnistValAcc === "number" && Number.isFinite(pipelineMnistValAcc);
  const hasRef =
    typeof charAccuracyVsReference === "number" && Number.isFinite(charAccuracyVsReference);
  if (!engineLabel && !hasRecorded && !hasRef) {
    return null;
  }
  return (
    <div className={styles.pipeRun} role="region" aria-label="OCR pipeline metrics for this run">
      <span className={styles.pipeRunTitle}>This run (API)</span>
      {engineLabel ? (
        <div className={styles.pipeRunRow}>
          <span className={styles.pipeRunKey}>OCR engine</span>
          <span className={styles.pipeRunVal}>{engineLabel}</span>
        </div>
      ) : null}
      {hasRecorded ? (
        <div className={styles.pipeRunRow}>
          <span className={styles.pipeRunKey}>Recorded MNIST validation (character-level)</span>
          <span className={styles.pipeRunVal}>{pctFromRatio(pipelineMnistValAcc)}</span>
        </div>
      ) : null}
      {hasRef ? (
        <div className={styles.pipeRunRow}>
          <span className={styles.pipeRunKey}>Accuracy vs reference transcript</span>
          <span className={styles.pipeRunVal}>{pctFromRatio(charAccuracyVsReference)}</span>
        </div>
      ) : (
        <p className={styles.pipeRunHint}>
          Send optional form field <code className={styles.reqCode}>reference_text</code> with{" "}
          <code className={styles.reqCode}>POST /ocr</code> to compute supervised character accuracy
          for this image (async jobs do not accept reference text yet).
        </p>
      )}
    </div>
  );
}

export function StageOcrCard({
  headerPillKind,
  headerPillLabel,
  text,
  confidence,
  ocrBackend = null,
  pipelineMnistValAcc = null,
  charAccuracyVsReference = null,
}) {
  const pct =
    typeof confidence === "number" && Number.isFinite(confidence)
      ? Math.round(Math.min(1, Math.max(0, confidence)) * 1000) / 10
      : 0;
  const fillWidth = `${pct}%`;

  const [accExpanded, setAccExpanded] = useState(false);
  const [accLoading, setAccLoading] = useState(false);
  const [accPayload, setAccPayload] = useState(null);
  const [accError, setAccError] = useState(null);
  /** Loaded on mount so the 95% gate vs recorded validation is always visible when metrics exist. */
  const [serverMetrics, setServerMetrics] = useState(null);
  const [metricsLoadFailed, setMetricsLoadFailed] = useState(false);

  const loadAccuracy = useCallback(async () => {
    try {
      const data = await fetchOcrAccuracy();
      setAccPayload(data);
      setServerMetrics(data);
      setMetricsLoadFailed(false);
      setAccError(null);
      return data;
    } catch {
      setMetricsLoadFailed(true);
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchOcrAccuracy();
        if (!cancelled) {
          setServerMetrics(data);
          setMetricsLoadFailed(false);
        }
      } catch {
        if (!cancelled) setMetricsLoadFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleAccuracy = useCallback(async () => {
    if (accExpanded) {
      setAccExpanded(false);
      return;
    }
    setAccExpanded(true);
    setAccLoading(true);
    setAccError(null);
    try {
      const data = await loadAccuracy();
      if (!data) {
        setAccError("Could not load OCR metrics from the server.");
      }
    } catch (e) {
      setAccError(e instanceof Error ? e.message : String(e));
      setAccPayload(null);
    } finally {
      setAccLoading(false);
    }
  }, [accExpanded, loadAccuracy]);

  return (
    <section className={styles.card}>
      <header className={styles.head}>
        <div className={styles.headLeft}>
          <span className={styles.stageNum}>01</span>
          <span className={styles.stageTitle}>OCR — MNIST CNN &amp; SimpleHTR</span>
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
          <span className={styles.confLabel}>CONFIDENCE (this prediction)</span>
          <div className={styles.barTrack}>
            <div className={styles.barFill} style={{ width: fillWidth }} />
          </div>
          <span className={styles.confVal}>{pct.toFixed(1)}%</span>
        </div>

        <PipelineRunMetrics
          ocrBackend={ocrBackend}
          pipelineMnistValAcc={pipelineMnistValAcc}
          charAccuracyVsReference={charAccuracyVsReference}
        />

        <div className={styles.reqBanner}>
          <span className={styles.reqBannerTitle}>Scoring requirement (MNIST CNN)</span>
          <p className={styles.reqBannerText}>
            ≥<strong>{CASE_CHAR_LEVEL_MIN_PCT}%</strong> character-level accuracy on the{" "}
            <strong>validation</strong> set (see problem statement). For 10 digit classes, this
            equals top-1 accuracy on the held-out validation split during training.
          </p>
        </div>

        <ValidationVsThreshold
          metrics={serverMetrics}
          failed={metricsLoadFailed}
        />

        <div className={styles.accActions}>
          <button
            type="button"
            className={styles.accBtn}
            onClick={toggleAccuracy}
            aria-expanded={accExpanded}
          >
            {accExpanded ? "Hide OCR accuracy" : "Show OCR accuracy"}
          </button>
        </div>

        {accExpanded ? (
          <div className={styles.accPanel} role="region" aria-label="OCR validation metrics">
            {accLoading ? (
              <p className={styles.accMuted}>Loading metrics…</p>
            ) : accError ? (
              <p className={styles.accErr}>{accError}</p>
            ) : accPayload ? (
              <AccMetricsBody payload={accPayload} />
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function ValidationVsThreshold({ metrics, failed }) {
  const m = metrics?.mnist_metrics;
  const r = m && !m.error ? ratioFromPayload(m) : null;
  const eligible = metrics?.mnist_scoring_eligible;
  const meets =
    typeof r === "number" ? r >= CASE_CHAR_LEVEL_MIN_PCT / 100 : null;

  if (failed && r == null) {
    return (
      <p className={styles.valPreviewMuted}>
        Could not reach OCR service for metrics — start Docker or check{" "}
        <code className={styles.reqCode}>GET /ocr/accuracy</code>.
      </p>
    );
  }

  if (r == null) {
    return (
      <p className={styles.valPreviewMuted}>
        No training metrics on server yet — run{" "}
        <code className={styles.reqCode}>python training/train_mnist_cnn.py</code> from{" "}
        <code className={styles.reqCode}>service_ocr/</code> to record validation accuracy vs the{" "}
        {CASE_CHAR_LEVEL_MIN_PCT}% gate.
      </p>
    );
  }

  return (
    <div className={styles.valPreview}>
      <div className={styles.valPreviewRow}>
        <span className={styles.valPreviewLabel}>Recorded validation (character-level)</span>
        <span
          className={
            meets === true
              ? styles.valPreviewStrongOk
              : meets === false
                ? styles.valPreviewStrongBad
                : styles.valPreviewStrong
          }
        >
          {pctFromRatio(r)}
        </span>
      </div>
      <div className={styles.valPreviewRow}>
        <span className={styles.valPreviewLabel}>Required for scoring</span>
        <span className={styles.valPreviewThreshold}>≥ {CASE_CHAR_LEVEL_MIN_PCT}.00%</span>
      </div>
      {typeof eligible === "boolean" ? (
        <p className={eligible ? styles.accEligibleInline : styles.accNotEligibleInline} role="status">
          {eligible
            ? "Meets the ≥95% validation gate on record."
            : "Below the ≥95% validation gate on record — retrain."}
        </p>
      ) : null}
    </div>
  );
}

function AccMetricsBody({ payload }) {
  const m = payload.mnist_metrics;
  const n = payload.noise_metrics;
  const eligible = payload.mnist_scoring_eligible;

  if (m?.error) {
    return <p className={styles.accErr}>{String(m.error)}</p>;
  }

  if (!payload.available && !m && !n) {
    return (
      <>
        <p className={styles.accMuted}>
          No training metrics file on the server yet. After you train the MNIST CNN, this panel
          shows test and validation accuracy.
        </p>
        <p className={styles.accHint}>{payload.hint}</p>
      </>
    );
  }

  return (
    <>
      {typeof eligible === "boolean" ? (
        <p className={eligible ? styles.accEligible : styles.accNotEligible} role="status">
          {eligible
            ? "MNIST CNN meets the case gate (≥95% validation accuracy on record)."
            : "MNIST CNN does not meet the ≥95% validation gate on record — retrain or check metrics."}
        </p>
      ) : null}
      {payload.stage1_stack ? (
        <p className={styles.accStack}>{payload.stage1_stack}</p>
      ) : null}
      <dl className={styles.accDl}>
      {m ? (
        <>
          <dt className={styles.accDt}>MNIST test accuracy</dt>
          <dd className={styles.accDd}>{pctFromRatio(m.test_accuracy)}</dd>
          <dt className={styles.accDt}>Best validation accuracy (character-level)</dt>
          <dd className={styles.accDd}>{pctFromRatio(m.best_validation_accuracy)}</dd>
          <dt className={styles.accDt}>Required threshold</dt>
          <dd className={styles.accDd}>{`≥ ${CASE_CHAR_LEVEL_MIN_PCT}%`}</dd>
          {typeof m.epochs_completed === "number" ? (
            <>
              <dt className={styles.accDt}>Epochs completed</dt>
              <dd className={styles.accDd}>{m.epochs_completed}</dd>
            </>
          ) : null}
        </>
      ) : (
        <>
          <dt className={styles.accDt}>MNIST metrics</dt>
          <dd className={styles.accDdMuted}>Not found — run training script.</dd>
        </>
      )}
      {n ? (
        <>
          <dt className={styles.accDt}>Clean test (noise eval)</dt>
          <dd className={styles.accDd}>{pctFromRatio(n.clean_test_accuracy)}</dd>
          <dt className={styles.accDt}>Gaussian noise (mean)</dt>
          <dd className={styles.accDd}>{pctFromRatio(n.gaussian_noise_mean_accuracy)}</dd>
          <dt className={styles.accDt}>Salt-and-pepper</dt>
          <dd className={styles.accDd}>{pctFromRatio(n.salt_and_pepper_accuracy)}</dd>
        </>
      ) : null}
    </dl>
    </>
  );
}
