from __future__ import annotations

from pathlib import Path

import numpy as np
import tensorflow as tf

from utils.image_preprocessing import preprocess_image_bytes

ROOT = Path(__file__).resolve().parents[1]
LEAF_MODEL_PATH = ROOT / "cnn_model" / "leaf_vs_non_leaf_model.keras"
LEAF_IMAGE_SIZE = 224


class LeafValidationError(ValueError):
    pass


def _load_leaf_model() -> tf.keras.Model:
    if not LEAF_MODEL_PATH.exists():
        raise RuntimeError(f"Leaf detection model not found at {LEAF_MODEL_PATH}")
    return tf.keras.models.load_model(str(LEAF_MODEL_PATH), compile=False)


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
    
    image_array = preprocess_image_bytes(
        image_bytes,
        (LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE),
        debug_label="leaf",
        expected_batch_shape=(1, LEAF_IMAGE_SIZE, LEAF_IMAGE_SIZE, 3),
        normalize=True,
    )
    
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
            class_index = int(np.argmax(prediction_flat))
            confidence = float(prediction_flat[class_index])
            is_leaf = class_index == 0

    return {
        "is_leaf": is_leaf,
        "confidence": float(confidence),
        "message": "Image contains a leaf" if is_leaf else "Sorry, this is not a leaf. Please put a leaf image.",
    }


def assert_leaf(image_bytes: bytes, threshold: float = 0.5) -> dict[str, object]:
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
