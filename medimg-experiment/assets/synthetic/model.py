"""EDITABLE: model definition. Candidates change this file (and train.py).

Tanh MLP. Classification uses the flattened image; segmentation shares the MLP
across pixels with intensity, 3x3 mean and coordinate features.
"""
import numpy as np

IMAGE_SIZE = 16


def features(task: str, images: np.ndarray) -> np.ndarray:
    if task == "classification":
        return images.reshape(len(images), -1)
    n, h, w = images.shape
    padded = np.pad(images, ((0, 0), (1, 1), (1, 1)), mode="edge")
    local = sum(padded[:, r:r + h, q:q + w] for r in range(3) for q in range(3)) / 9.0
    ys, xs = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    return np.stack([images, local, np.broadcast_to(xs, (n, h, w)), np.broadcast_to(ys, (n, h, w)),
                     np.broadcast_to(xs * xs + ys * ys, (n, h, w))], axis=-1).reshape(-1, 5)


def init(input_size: int, width: int, seed: int) -> dict:
    rng = np.random.default_rng(np.random.SeedSequence([seed, 1301]))
    return {"w1": rng.normal(0, 1 / np.sqrt(input_size), (input_size, width)), "b1": np.zeros(width),
            "w2": rng.normal(0, 1 / np.sqrt(width), (width, 1)), "b2": np.zeros(1)}


def forward(x: np.ndarray, w: dict) -> tuple[np.ndarray, np.ndarray]:
    hidden = np.tanh(x @ w["w1"] + w["b1"])
    return hidden, hidden @ w["w2"] + w["b2"]


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def predict(task: str, images: np.ndarray, w: dict) -> np.ndarray:
    p = sigmoid(forward(features(task, images), w)[1]).reshape(-1)
    return p if task == "classification" else p.reshape(len(images), IMAGE_SIZE, IMAGE_SIZE)
