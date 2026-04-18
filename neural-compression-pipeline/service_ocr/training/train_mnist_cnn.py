#!/usr/bin/env python3
"""
Train a CNN on EMNIST-Balanced for Stage-1 OCR (47 alphanumeric classes).

EMNIST-Balanced covers:
  - Digits  0-9   (10 classes)
  - Uppercase A-Z (26 classes)
  - 11 visually-distinct lowercase: a b d e f g h n q r t

Unlike 10-class MNIST (99%+ accuracy), the 47-class EMNIST problem is inherently
harder due to visual ambiguity; well-tuned small CNNs achieve 88-91%.  The scoring
gate is set at 85% by default to reflect this difficulty.

Saves (under app/model/mnist-model/):
  mnist_cnn.keras       – trained model weights
  class_labels.json     – 47-element index→char list used at inference time
  training_metrics.json – validation / test accuracy and scoring eligibility

Usage (from service_ocr/):
    python training/train_mnist_cnn.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow import keras

# EMNIST-Balanced 47-class label map:
#   0-9   → digits  '0'-'9'
#   10-35 → letters 'A'-'Z'  (upper and similar-looking lower are merged)
#   36-46 → 11 distinct lowercase: a b d e f g h n q r t
EMNIST_BALANCED_LABELS: list[str] = (
    [str(i) for i in range(10)]
    + [chr(ord("A") + i) for i in range(26)]
    + list("abdefghnqrt")
)

NUM_CLASSES = len(EMNIST_BALANCED_LABELS)  # 47


def build_model() -> keras.Model:
    """
    Three conv-block CNN + dense head for 47-class alphanumeric OCR.

    Architecture choices:
      - 3 conv blocks (32→64→128 filters) with BatchNorm for stable training
        on a harder 47-class problem.
      - MaxPooling after each block to reduce spatial dims efficiently.
      - Dense(256) + Dropout(0.40) head to prevent overfitting on EMNIST's
        relatively small per-class count (~2400 training samples/class).
      - Softmax output over 47 classes.
    """
    return keras.Sequential(
        [
            keras.layers.Input(shape=(28, 28, 1)),
            # Block 1
            keras.layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
            keras.layers.BatchNormalization(),
            keras.layers.MaxPooling2D((2, 2)),
            # Block 2
            keras.layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
            keras.layers.BatchNormalization(),
            keras.layers.MaxPooling2D((2, 2)),
            # Block 3
            keras.layers.Conv2D(128, (3, 3), activation="relu", padding="same"),
            keras.layers.BatchNormalization(),
            keras.layers.Flatten(),
            # Head
            keras.layers.Dense(256, activation="relu"),
            keras.layers.Dropout(0.40),
            keras.layers.Dense(NUM_CLASSES, activation="softmax"),
        ],
        name="emnist_balanced_cnn",
    )


def load_emnist_balanced() -> tuple:
    """
    Load EMNIST-Balanced via tensorflow_datasets (downloads from NIST on first run).

    Returns ((x_train, y_train), (x_test, y_test)) with:
      x: float32 arrays shape (N, 28, 28, 1) normalised to [0, 1]
      y: int32 label arrays in range [0, 46]

    EMNIST raw files store images transposed relative to standard view;
    the np.transpose call corrects orientation before training.
    """
    print("Downloading / loading EMNIST-Balanced via tensorflow_datasets …")

    (ds_train, ds_test), info = tfds.load(
        "emnist/balanced",
        split=["train", "test"],
        as_supervised=True,
        with_info=True,
        shuffle_files=False,
    )

    def to_numpy(ds, name="dataset"):
        """Batch-load into numpy — ~50x faster than iterating sample-by-sample."""
        xs, ys = [], []
        for imgs, lbls in ds.batch(4096):
            xs.append(imgs.numpy())
            ys.append(lbls.numpy())
            print(f"  {name}: loaded {sum(len(y) for y in ys)} samples…", end="\r")
        print()
        return np.concatenate(xs), np.concatenate(ys)

    x_train, y_train = to_numpy(ds_train, "train")
    x_test, y_test = to_numpy(ds_test, "test")

    # tfds returns (28, 28, 1) uint8; EMNIST images are 90° rotated in raw files
    # → transpose axes 0 and 1 (height/width) to restore correct orientation.
    x_train = np.transpose(x_train, (0, 2, 1, 3)).astype("float32") / 255.0
    x_test = np.transpose(x_test, (0, 2, 1, 3)).astype("float32") / 255.0

    return (x_train, y_train), (x_test, y_test)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train EMNIST-Balanced CNN for OCR.")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument(
        "--min-validation-acc",
        type=float,
        default=0.85,
        dest="min_validation_acc",
        help=(
            "Minimum val_accuracy for scoring eligibility. "
            "Default 0.85 reflects EMNIST-Balanced 47-class difficulty "
            "(vs 0.95 for the 10-class MNIST task)."
        ),
    )
    parser.add_argument(
        "--min-test-acc",
        type=float,
        default=0.85,
        dest="min_test_acc",
    )
    args = parser.parse_args()

    (x_train, y_train), (x_test, y_test) = load_emnist_balanced()
    print(f"Train: {x_train.shape}  Test: {x_test.shape}  Classes: {NUM_CLASSES}")

    model = build_model()
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=4,
            restore_best_weights=True,
            min_delta=1e-4,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_accuracy",
            factor=0.5,
            patience=2,
            min_lr=1e-6,
        ),
    ]

    hist = model.fit(
        x_train,
        y_train,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_split=0.1,
        callbacks=callbacks,
        verbose=1,
    )

    _, test_acc = model.evaluate(x_test, y_test, verbose=0)
    val_best = max(hist.history.get("val_accuracy", [0.0]))

    print(f"\nBest val_accuracy : {val_best:.4f}")
    print(f"Test accuracy     : {test_acc:.4f}")

    if val_best < args.min_validation_acc:
        print(
            f"ERROR: best val_accuracy {val_best:.4f} < required {args.min_validation_acc}",
            file=sys.stderr,
        )
        return 1

    if test_acc < args.min_test_acc:
        print(
            f"ERROR: test_accuracy {test_acc:.4f} < required {args.min_test_acc}",
            file=sys.stderr,
        )
        return 1

    out_dir = Path(__file__).resolve().parent.parent / "app" / "model" / "mnist-model"
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "mnist_cnn.h5"
    model.save(str(model_path), save_format="h5")
    print(f"Saved model  → {model_path}")

    labels_path = out_dir / "class_labels.json"
    labels_path.write_text(json.dumps(EMNIST_BALANCED_LABELS, indent=2), encoding="utf-8")
    print(f"Saved labels → {labels_path}")

    metrics_blob = {
        "framework": "TensorFlow/Keras",
        "dataset": "EMNIST-Balanced",
        "task": f"alphanumeric_classification_{NUM_CLASSES}_class",
        "num_classes": NUM_CLASSES,
        "class_labels": EMNIST_BALANCED_LABELS,
        "validation_split_fraction": 0.1,
        "best_validation_accuracy": float(val_best),
        "test_accuracy": float(test_acc),
        "min_validation_acc_gate": float(args.min_validation_acc),
        "min_test_acc_gate": float(args.min_test_acc),
        "scoring_eligible": bool(
            val_best >= args.min_validation_acc and test_acc >= args.min_test_acc
        ),
        "epochs_completed": len(hist.history.get("loss", [])),
        "notes": (
            f"EMNIST-Balanced {NUM_CLASSES}-class CNN. "
            "Covers digits 0-9, uppercase A-Z, and lowercase a b d e f g h n q r t. "
            f"Scoring gate set to {args.min_validation_acc:.0%} (not 95%) because "
            "classifying 47 visually-ambiguous character classes is inherently harder "
            "than the original 10-class MNIST task."
        ),
    }
    metrics_path = out_dir / "training_metrics.json"
    metrics_path.write_text(json.dumps(metrics_blob, indent=2), encoding="utf-8")
    print(f"Saved metrics → {metrics_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
