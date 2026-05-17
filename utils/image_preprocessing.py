from __future__ import annotations

import os

import numpy as np
import tensorflow as tf

DEBUG_IMAGE_PIPELINE = os.getenv("DEBUG_IMAGE_PIPELINE", "1").strip().lower() not in {"0", "false", "no"}


def _log_shape(stage: str, tensor: tf.Tensor | np.ndarray, debug_label: str) -> None:
    if not DEBUG_IMAGE_PIPELINE:
        return

    tensor_shape = tuple(getattr(tensor, "shape", ()))
    try:
        dynamic_shape = tuple(tf.shape(tensor).numpy())
    except Exception:
        dynamic_shape = tensor_shape

    dtype = getattr(tensor, "dtype", None)
    print(f"[{debug_label}] {stage}: shape={tensor_shape}, dynamic_shape={dynamic_shape}, dtype={dtype}")


def preprocess_image_bytes(
    image_bytes: bytes,
    target_size: tuple[int, int],
    *,
    debug_label: str,
    expected_batch_shape: tuple[int, int, int, int] | None = None,
    normalize: bool = True,
) -> np.ndarray:
    """
    Decode, resize, normalize, and batch an image for model inference.

    Logs each preprocessing step when DEBUG_IMAGE_PIPELINE is enabled.
    """
    image_tensor = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    _log_shape("original image", image_tensor, debug_label)

    resized_tensor = tf.image.resize(image_tensor, target_size)
    _log_shape("resized image", resized_tensor, debug_label)

    prepared_tensor = tf.cast(resized_tensor, tf.float32)
    if normalize:
        prepared_tensor = prepared_tensor / 255.0
        _log_shape("normalized image", prepared_tensor, debug_label)

    batch_tensor = tf.expand_dims(prepared_tensor, axis=0)
    _log_shape("expanded batch", batch_tensor, debug_label)

    batch_array = batch_tensor.numpy()
    _log_shape("final tensor before prediction", batch_array, debug_label)

    if expected_batch_shape is not None and tuple(batch_array.shape) != expected_batch_shape:
        raise ValueError(
            f"{debug_label} preprocessing produced shape {batch_array.shape}, expected {expected_batch_shape}"
        )

    return batch_array
