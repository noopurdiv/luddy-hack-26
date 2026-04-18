#!/usr/bin/env python3
"""
Train a CNN on MNIST for Stage-1 OCR (digit classification).

Saves ``mnist_cnn.keras`` under ``app/model/mnist-model/``.

**Scoring eligibility (case rules):** ≥95% **character-level** accuracy on the **held-out
validation split** (10% of training). For MNIST digit classification, top-1 class accuracy
equals per-digit character correctness. This script **refuses to save weights** unless both
validation and test accuracies meet the configured floors (default 95%).

Usage (from ``service_ocr/``):

    python training/train_mnist_cnn.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import tensorflow as tf
from tensorflow import keras


def build_model() -> keras.Model:
    """Small CNN: two conv blocks + dense head (TensorFlow / Keras)."""
    return keras.Sequential(
        [
            keras.layers.Input(shape=(28, 28, 1)),
            keras.layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(128, activation="relu"),
            keras.layers.Dropout(0.35),
            keras.layers.Dense(10, activation="softmax"),
        ],
        name="mnist_digit_cnn",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Train MNIST CNN for OCR microservice.")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument(
        "--min-validation-acc",
        type=float,
        default=0.95,
        dest="min_validation_acc",
        help="Minimum best val_accuracy (validation split) for scoring eligibility — case default 0.95",
    )
    parser.add_argument(
        "--min-test-acc",
        type=float,
        default=0.95,
        dest="min_test_acc",
        help="Minimum MNIST test_accuracy after training (sanity check; default 0.95)",
    )
    args = parser.parse_args()

    (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
    x_train = (x_train.astype("float32") / 255.0)[..., None]
    x_test = (x_test.astype("float32") / 255.0)[..., None]

    model = build_model()
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=3,
            restore_best_weights=True,
            min_delta=1e-4,
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

    print(f"Best val_accuracy (validation set): {val_best:.4f}")
    print(f"mnist test_accuracy: {test_acc:.4f}")

    if val_best < args.min_validation_acc:
        print(
            f"ERROR: best val_accuracy {val_best:.4f} < required {args.min_validation_acc} "
            "(validation set — model NOT eligible for scoring per case rules)",
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
    path = out_dir / "mnist_cnn.keras"
    model.save(path)
    print(f"Saved model to {path}")

    metrics_blob = {
        "framework": "TensorFlow/Keras",
        "dataset": "MNIST",
        "task": "digit_classification_10_class",
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
            "Character-level accuracy for digits 0–9 equals top-1 classification accuracy "
            "on MNIST. Case requires ≥95% on the validation set; this run met the gates above."
        ),
    }
    (out_dir / "training_metrics.json").write_text(
        json.dumps(metrics_blob, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote metrics to {out_dir / 'training_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
