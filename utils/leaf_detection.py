<<<<<<< HEAD
=======
# from __future__ import annotations

# from pathlib import Path

# import numpy as np
# import tensorflow as tf

# from utils.image_preprocessing import preprocess_image_bytes

# ROOT = Path(__file__).resolve().parents[1]
# CNN_MODEL_DIR = ROOT / "cnn_model"
# LEAF_IMAGE_SIZE = 224


# def _resolve_cnn_model_file(filename: str) -> Path:
#     direct = CNN_MODEL_DIR / filename
#     nested = CNN_MODEL_DIR / "cnn_model" / filename
#     if direct.exists():
#         return direct
#     if nested.exists():
#         return nested
#     raise FileNotFoundError(f"Leaf detection model not found at {direct} or {nested}")


# LEAF_MODEL_PATH = _resolve_cnn_model_file("leaf_vs_non_leaf_model.keras")


# class LeafValidationError(ValueError):
#     pass


# def _load_leaf_model() -> tf.keras.Model:
#     if not LEAF_MODEL_PATH.exists():
#         raise RuntimeError(f"Leaf detection model not found at {LEAF_MODEL_PATH}")
#     return tf.keras.models.load_model(str(LEAF_MODEL_PATH), compile=False)


# # CHANGED: avoid global leaf model caching to prevent stale state between predictions.
# # LEAF_MODEL = _load_leaf_model()


# def _get_leaf_model() -> tf.keras.Model:
#     """Load a fresh leaf model instance for each prediction call."""
#     return tf.keras.models.load_model(str(LEAF_MODEL_PATH), compile=False)


# def _clear_model_state(model: tf.keras.Model):
#     """Clear model state between predictions to prevent state accumulation."""
#     for layer in model.layers:
#         if hasattr(layer, 'reset_states'):
#             layer.reset_states()


# def predict_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
#     """
#     Predict if image contains a leaf.
    
#     Args:
#         image_bytes: Raw image bytes
#         threshold: Confidence threshold (0-1)
    
#     Returns:
#         Dict with is_leaf, confidence, and message
#     """
#     # Load a fresh model for this inference and clear any stateful layers.
#     leaf_model = _get_leaf_model()
#     _clear_model_state(leaf_model)
    
#     image_array = preprocess_image_bytes(
#         image_bytes,
#         (LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE),
#         debug_label="leaf",
#         expected_batch_shape=(1, LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE, 3),
#         normalize=True,
#     )
    
#     # Run prediction on the fresh model instance and clear TF session afterward.
#     print(f"[leaf] model expected input shape: {leaf_model.input_shape}")
#     print(f"[leaf] tensor fed to model: {image_array.shape}")
#     raw_prediction = leaf_model.predict(image_array, verbose=0)
#     tf.keras.backend.clear_session()  # CHANGED: clear TF session after prediction to avoid caching/stale graph state
    
#     # Extract first batch element as numpy array
#     prediction_output = np.asarray(raw_prediction[0], dtype=np.float32)
    
#     # Handle both binary (scalar) and multi-class (vector) outputs
#     if prediction_output.ndim == 0:
#         # Single scalar output (binary sigmoid)
#         confidence = float(prediction_output)
#         is_leaf = confidence >= threshold
#     else:
#         # Flatten in case of unexpected shape, then process
#         prediction_flat = prediction_output.flatten()
        
#         if len(prediction_flat) == 1:
#             # Single value in array
#             confidence = float(prediction_flat[0])
#             is_leaf = confidence >= threshold
#         else:
#             # Multiple outputs - class 0 = leaf, class 1 = non_leaf
#             class_index = int(np.argmax(prediction_flat))
#             confidence = float(prediction_flat[class_index])
#             is_leaf = class_index == 0

#     return {
#         "is_leaf": is_leaf,
#         "confidence": float(confidence),
#         "message": "Image contains a leaf" if is_leaf else "Sorry, this is not a leaf. Please put a leaf image.",
#     }


# def assert_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
#     """
#     Assert that image contains a leaf. Raises LeafValidationError if not.
    
#     Args:
#         image_bytes: Raw image bytes
#         threshold: Confidence threshold (0-1)
    
#     Returns:
#         Prediction dict if valid
        
#     Raises:
#         LeafValidationError: If image does not contain a leaf
#     """
#     result = predict_leaf(image_bytes=image_bytes, threshold=threshold)
#     if not result["is_leaf"]:
#         raise LeafValidationError(result["message"])
#     return result



# leaf_detection.py
>>>>>>> 53c2c75 (chat issue resolve)
from __future__ import annotations

from pathlib import Path

import numpy as np
import tensorflow as tf

from utils.image_preprocessing import preprocess_image_bytes

ROOT = Path(__file__).resolve().parents[1]
<<<<<<< HEAD
LEAF_MODEL_PATH = ROOT / "cnn_model" / "leaf_vs_non_leaf_model.keras"
LEAF_IMAGE_SIZE = 224


=======
CNN_MODEL_DIR = ROOT / "cnn_model"
LEAF_IMAGE_SIZE = 224


def _resolve_cnn_model_file(filename: str) -> Path:
    direct = CNN_MODEL_DIR / filename
    nested = CNN_MODEL_DIR / "cnn_model" / filename
    if direct.exists():
        return direct
    if nested.exists():
        return nested
    raise FileNotFoundError(f"Leaf detection model not found at {direct} or {nested}")


LEAF_MODEL_PATH = _resolve_cnn_model_file("leaf_vs_non_leaf_model.keras")


>>>>>>> 53c2c75 (chat issue resolve)
class LeafValidationError(ValueError):
    pass


def _load_leaf_model() -> tf.keras.Model:
    if not LEAF_MODEL_PATH.exists():
        raise RuntimeError(f"Leaf detection model not found at {LEAF_MODEL_PATH}")
    return tf.keras.models.load_model(str(LEAF_MODEL_PATH), compile=False)


<<<<<<< HEAD
LEAF_MODEL = _load_leaf_model()


def _clear_model_state():
    """Clear model state between predictions to prevent state accumulation."""
    for layer in LEAF_MODEL.layers:
        if hasattr(layer, 'reset_states'):
            layer.reset_states()


def predict_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
    """
    Predict if image contains a leaf.
    
    Args:
        image_bytes: Raw image bytes
        threshold: Confidence threshold (0-1)
    
    Returns:
        Dict with is_leaf, confidence, and message
    """
    # Clear any accumulated model state
    _clear_model_state()
    
=======
# ✅ Load once at module level - same pattern as disease model
LEAF_MODEL = _load_leaf_model()


def predict_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
>>>>>>> 53c2c75 (chat issue resolve)
    image_array = preprocess_image_bytes(
        image_bytes,
        (LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE),
        debug_label="leaf",
        expected_batch_shape=(1, LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE, 3),
        normalize=True,
    )
<<<<<<< HEAD
    
    # Run prediction - ensure fresh array conversion to avoid state issues
    print(f"[leaf] model expected input shape: {LEAF_MODEL.input_shape}")
    print(f"[leaf] tensor fed to model: {image_array.shape}")
    raw_prediction = LEAF_MODEL.predict(image_array, verbose=0)
    
    # Extract first batch element as numpy array
    prediction_output = np.asarray(raw_prediction[0], dtype=np.float32)
    
    # Handle both binary (scalar) and multi-class (vector) outputs
    if prediction_output.ndim == 0:
        # Single scalar output (binary sigmoid)
        confidence = float(prediction_output)
        is_leaf = confidence >= threshold
    else:
        # Flatten in case of unexpected shape, then process
        prediction_flat = prediction_output.flatten()
        
        if len(prediction_flat) == 1:
            # Single value in array
            confidence = float(prediction_flat[0])
            is_leaf = confidence >= threshold
        else:
            # Multiple outputs - class 0 = leaf, class 1 = non_leaf
=======

    print(f"[leaf] model expected input shape: {LEAF_MODEL.input_shape}")
    print(f"[leaf] tensor fed to model: {image_array.shape}")

    # ✅ Single predict call, store result
    raw_prediction = LEAF_MODEL.predict(image_array, verbose=0)
    # ✅ No clear_session() - it destroys shared TF graph state

    prediction_output = np.asarray(raw_prediction[0], dtype=np.float32)

    if prediction_output.ndim == 0:
        confidence = float(prediction_output)
        is_leaf = confidence >= threshold
    else:
        prediction_flat = prediction_output.flatten()
        if len(prediction_flat) == 1:
            confidence = float(prediction_flat[0])
            is_leaf = confidence >= threshold
        else:
>>>>>>> 53c2c75 (chat issue resolve)
            class_index = int(np.argmax(prediction_flat))
            confidence = float(prediction_flat[class_index])
            is_leaf = class_index == 0

    return {
        "is_leaf": is_leaf,
        "confidence": float(confidence),
        "message": "Image contains a leaf" if is_leaf else "Sorry, this is not a leaf. Please put a leaf image.",
    }


def assert_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
<<<<<<< HEAD
    """
    Assert that image contains a leaf. Raises LeafValidationError if not.
    
    Args:
        image_bytes: Raw image bytes
        threshold: Confidence threshold (0-1)
    
    Returns:
        Prediction dict if valid
        
    Raises:
        LeafValidationError: If image does not contain a leaf
    """
    result = predict_leaf(image_bytes=image_bytes, threshold=threshold)
    if not result["is_leaf"]:
        raise LeafValidationError(result["message"])
    return result
=======
    result = predict_leaf(image_bytes=image_bytes, threshold=threshold)
    if not result["is_leaf"]:
        raise LeafValidationError(result["message"])
    return result
>>>>>>> 53c2c75 (chat issue resolve)
