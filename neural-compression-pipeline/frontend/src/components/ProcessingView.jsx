import s from "./ProcessingView.module.css";

export function ProcessingView({ stage, filename }) {
  return (
    <div className={s.root}>
      <div className={s.card}>
        <div className={s.spinner}>
          <div className={s.spinnerRing}/>
          <div className={s.spinnerDot}/>
        </div>
        <h2 className={s.title}>Processing Document</h2>
        <p className={s.filename}>{filename}</p>
        <p className={s.stage}>{stage || "Initializing pipeline…"}</p>
        <div className={s.steps}>
          <div className={`${s.step} ${stage.includes("OCR") || stage.includes("Extracting") ? s.stepActive : stage ? s.stepDone : ""}`}>
            <div className={s.stepDot}/>
            <span>Neural OCR Extraction</span>
          </div>
          <div className={s.stepLine}/>
          <div className={`${s.step} ${stage.includes("Compress") || stage.includes("Huffman") ? s.stepActive : stage.includes("Verify") || stage.includes("lossless") ? s.stepDone : ""}`}>
            <div className={s.stepDot}/>
            <span>Adaptive Huffman Compression</span>
          </div>
          <div className={s.stepLine}/>
          <div className={`${s.step} ${stage.includes("Verify") || stage.includes("lossless") ? s.stepActive : ""}`}>
            <div className={s.stepDot}/>
            <span>Lossless Verification</span>
          </div>
        </div>
      </div>
    </div>
  );
}
