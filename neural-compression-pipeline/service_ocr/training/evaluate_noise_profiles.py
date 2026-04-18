#!/usr/bin/env python3
"""
Evaluate MNIST CNN under two noise profiles (graduate requirement):

  * additive Gaussian noise on normalized pixels
  * salt-and-pepper noise

Requires trained ``app/model/mnist-model/mnist_cnn.keras`` (run ``train_mnist_cnn.py``).

Usage::

    python training/evaluate_noise_profiles.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from tensorflow import keras


def add_gaussian_noise(x: np.ndarray, sigma: float = 0.35) -> np.ndarray:
    noise = np.random.randn(*x.shape).astype(np.float32) * sigma
    return np.clip(x + noise, 0.0, 1.0)


def add_salt_and_pepper(x: np.ndarray, salt: float = 0.04, pepper: float = 0.04) -> np.ndarray:
    out = np.array(x, copy=True)
    u = np.random.random(x.shape)
    out[u < salt] = 1.0
    out[u > 1.0 - pepper] = 0.0
    return out


def main() -> int:
    model_path = (
        Path(__file__).resolve().parent.parent / "app" / "model" / "mnist-model" / "mnist_cnn.keras"
    )
    if not model_path.is_file():
        print(f"Missing model: {model_path}\nTrain with: python training/train_mnist_cnn.py", file=sys.stderr)
        return 1

    model = keras.models.load_model(model_path)

    (_, _), (x_test, y_test) = keras.datasets.mnist.load_data()
    x_test = (x_test.astype("float32") / 255.0)[..., None]

    # Gaussian-noise accuracy (average over 3 draws for stability)
    gauss_acc = []
    for seed in range(3):
        np.random.seed(seed)
        noisy = add_gaussian_noise(x_test, sigma=0.35)
        _, acc = model.evaluate(noisy, y_test, verbose=0)
        gauss_acc.append(acc)
    gauss_mean = float(np.mean(gauss_acc))

    # Salt-and-pepper (single deterministic draw with fixed seed)
    np.random.seed(42)
    sp = add_salt_and_pepper(x_test)
    _, sp_acc = model.evaluate(sp, y_test, verbose=0)

    clean_acc = float(model.evaluate(x_test, y_test, verbose=0)[1])

    print(f"clean test_accuracy:           {clean_acc:.4f}")
    print(f"gaussian noise mean accuracy:  {gauss_mean:.4f}")
    print(f"salt-and-pepper test_accuracy: {sp_acc:.4f}")

    out_dir = model_path.parent
    noise_blob = {
        "dataset": "MNIST",
        "clean_test_accuracy": clean_acc,
        "gaussian_noise_mean_accuracy": gauss_mean,
        "gaussian_sigma": 0.35,
        "salt_and_pepper_accuracy": float(sp_acc),
        "salt_fraction": 0.04,
        "pepper_fraction": 0.04,
        "notes": "Noise profiles per graduate rubric (Gaussian + salt-and-pepper).",
    }
    (out_dir / "noise_metrics.json").write_text(
        json.dumps(noise_blob, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'noise_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
