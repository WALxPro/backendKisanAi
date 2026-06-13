from __future__ import annotations

from pathlib import Path

import numpy as np
import tensorflow as tf

from utils.image_preprocessing import preprocess_image_bytes

ROOT = Path(__file__).resolve().parents[1]
CNN_MODEL_DIR = ROOT / "cnn_model"
LEAF_IMAGE_SIZE = 224


def _resolve_cnn_model_file(filename: str) -> Path:
    """cnn_model/ folder ke andar file dhundo — flat ya nested dono support."""
    direct = CNN_MODEL_DIR / filename
    nested = CNN_MODEL_DIR / "cnn_model" / filename
    if direct.exists():
        return direct
    if nested.exists():
        return nested
    raise FileNotFoundError(
        f"Model file nahi mili:\n  {direct}\n  {nested}"
    )


LEAF_MODEL_PATH = _resolve_cnn_model_file("leaf_vs_non_leaf_model.keras")


class LeafValidationError(ValueError):
    """Raise hoti hai jab image mein leaf nahi hoti."""
    pass


def _load_leaf_model() -> tf.keras.Model:
    if not LEAF_MODEL_PATH.exists():
        raise RuntimeError(f"Leaf model nahi mila: {LEAF_MODEL_PATH}")
    return tf.keras.models.load_model(str(LEAF_MODEL_PATH), compile=False)


# ✅ Module load hote waqt ek baar load — disease model jaisi pattern
LEAF_MODEL = _load_leaf_model()


def predict_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
    """
    Check karo ke image mein leaf hai ya nahi.

    Args:
        image_bytes : Raw image bytes (mobile se aai hui photo)
        threshold   : Is se kam confidence = not a leaf (default 0.5)

    Returns:
        {
            "is_leaf"    : bool,
            "confidence" : float (0.0 – 1.0),
            "message"    : str
        }
    """
    image_array = preprocess_image_bytes(
        image_bytes,
        (LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE),
        debug_label="leaf",
        expected_batch_shape=(1, LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE, 3),
        normalize=True,
    )

    print(f"[leaf] model input shape : {LEAF_MODEL.input_shape}")
    print(f"[leaf] tensor shape      : {image_array.shape}")

    # ✅ Ek hi predict call — clear_session() nahi (shared TF graph kharab hoti hai)
    raw_prediction = LEAF_MODEL.predict(image_array, verbose=0)
    prediction_output = np.asarray(raw_prediction[0], dtype=np.float32)

    # Model output ke teeno cases handle karo
    if prediction_output.ndim == 0:
        # Binary sigmoid — single scalar
        confidence = float(prediction_output)
        is_leaf = confidence >= threshold

    else:
        prediction_flat = prediction_output.flatten()

        if len(prediction_flat) == 1:
            # Single value array — binary sigmoid
            confidence = float(prediction_flat[0])
            is_leaf = confidence >= threshold
        else:
            # Multi-class — class 0 = leaf, class 1 = non_leaf
            class_index = int(np.argmax(prediction_flat))
            confidence = float(prediction_flat[class_index])
            is_leaf = class_index == 0

    return {
        "is_leaf": is_leaf,
        "confidence": confidence,
        "message": (
            "Image mein leaf hai ✅"
            if is_leaf else
            "❌ Yeh leaf nahi hai. Please wheat patti ki photo bhejein."
        ),
    }


def assert_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
    """
    Leaf honi chahiye — nahi hai toh LeafValidationError raise karo.

    Args:
        image_bytes : Raw image bytes
        threshold   : Confidence threshold

    Returns:
        predict_leaf() ka result (agar leaf hai)

    Raises:
        LeafValidationError: Agar leaf nahi hai
    """
    result = predict_leaf(image_bytes=image_bytes, threshold=threshold)
    if not result["is_leaf"]:
        raise LeafValidationError(result["message"])
    return result