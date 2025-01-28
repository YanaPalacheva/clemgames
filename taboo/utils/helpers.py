import subprocess
import sys
import json

import spacy
import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from typing import Tuple, List, Optional

LANGUAGE_CONFIG_FILE = "language_config.json"
nltk.download('stopwords', quiet=True)

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

def load_language_config(language):
    """Load language-specific configurations from the JSON file."""
    with open(LANGUAGE_CONFIG_FILE, "r") as config_file:
        config = json.load(config_file)
    if language not in config:
        raise ValueError(f"Language '{language}' is not supported in the configuration file.")
    return config[language]


def get_stopwords_and_stemmer(lang_config: dict) -> Tuple[List[str], Optional[SnowballStemmer]]:
    stopwords_source = lang_config["stopwords_source"]
    full_language = lang_config.get("full_language")

    if stopwords_source == 'nltk':
        stopwords_list = stopwords.words(full_language)
    else:
        stopwords_list = []
        print(f"stopwords for language: {full_language} are not provided by NLTK")

    if full_language in SnowballStemmer.languages:
        stemmer = SnowballStemmer(full_language)
    else:
        stemmer = None
        raise ValueError(f"Stemmer for language: {full_language} are not provided by NLTK!")

    return stopwords_list, stemmer

