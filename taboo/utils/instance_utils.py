import subprocess
import sys
import os

import nltk
import spacy
from nltk.stem.snowball import SnowballStemmer
from nltk.corpus import stopwords

from clemcore.clemgame import GameResourceLocator


nltk.download('stopwords', quiet=True)


# InstanceUtils: handles all resources necessary for the instance generation
class InstanceUtils(GameResourceLocator):
    def __init__(self, language: str, game_path):
        super().__init__(path=game_path)
        self.lang_config = self.load_json("resources/langconfig.json").get(language)
        self.language = language
        self.resource_path = f"resources/target_words/{self.language}/"
        self.manual_related_words_path = f"{self.resource_path}/related_words.json"
        self._taboo_keys_path = "taboo_keys"

    def load_spacy_model(self):
        """
        Load a spaCy model for the current language. If the model is not downloaded, download it first.

        :return: The loaded spaCy model.
        """
        model = self.lang_config.get("spacy_model")
        try:
            return spacy.load(model)
        except OSError:
            print(f"Model '{model}' not found. Downloading it now...")
            subprocess.run([sys.executable, "-m", "spacy", "download", model], check=True)
            return spacy.load(model)

    def get_stemmer(self):
        full_language = self.lang_config.get("full_language")
        if full_language in SnowballStemmer.languages:
            stemmer = SnowballStemmer(full_language)
        else:
            raise ValueError(f"Stemmer for language: {full_language} are not provided by NLTK!")

        return stemmer

    def get_stopwords(self):
        full_language = self.lang_config.get("full_language")
        stopwords_source = self.lang_config["stopwords_source"]

        if stopwords_source == 'nltk':
            stopwords_list = stopwords.words(full_language)
        else:
            stopwords_list = []
            print(f"Stopwords for language: {full_language} are not provided by NLTK")

        return stopwords_list

    def load_manual_related_words(self) -> {}:
        if not os.path.exists(self.manual_related_words_path):
            print(f"No manual related words found for language {self.language}!")
            return {}
        return self.load_json(self.manual_related_words_path)

    def load_openai_api_key(self):
        key = self.load_json(self._taboo_keys_path).get('openai_api_key', "")
        if not key:
            raise ValueError(f"OpenAI API key is not set. Set it in {self._taboo_keys_path}.json")
        return key

