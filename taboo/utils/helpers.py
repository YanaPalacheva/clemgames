import subprocess
import sys

import spacy

# spacy
def load_spacy_model(model_name="en_core_web_sm"):
    """
    Load a spaCy model. If the model is not downloaded, download it first.

    :param model_name: The name of the spaCy model to load.
    :return: The loaded spaCy model.
    """
    try:
        return spacy.load(model_name)
    except OSError:
        print(f"Model '{model_name}' not found. Downloading it now...")
        subprocess.run([sys.executable, "-m", "spacy", "download", model_name], check=True)
        return spacy.load(model_name)