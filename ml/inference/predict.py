import joblib
import pandas as pd

from backend.app.core.config import MODEL_FILE

# Global cached model
model = None


def load_model():
    global model

    if model is None:
        print("Loading trained model into memory...")
        model = joblib.load(MODEL_FILE)

    return model


def predict_price(features: dict):

    model_instance = load_model()

    df = pd.DataFrame([features])

    prediction = model_instance.predict(df)[0]

    return prediction

