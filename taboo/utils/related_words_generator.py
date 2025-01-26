import json
from pathlib import Path

import requests
import openai
import logging

from taboo.utils.en.select_taboo_words import is_function_word
from taboo.utils.helpers import load_spacy_model

logger = logging.getLogger(__name__)

class RelatedWordGenerator:
    def __init__(self, language, n_related_words, openai_api_key=None):
        self.language = language
        self.n_related_words = n_related_words
        self.openai_api_key = openai_api_key
        self.tagger = self.load_tagger()

        if language == 'ru':
            source = Path(__file__).resolve().parents[1] / "resources" / "target_words" / "ru" / "related_words.json"
            self.ru_manual_related_words = json.loads(source.read_text(encoding="utf-8"))

    def manual(self, word):
        if self.language == 'ru':
            words = self.ru_manual_related_words.get(word, [])
            if len(words) < self.n_related_words:
                print(f'{len(words)} related words found for word {word}! {self.n_related_words} words are expected.')
            return words
        else:
            print(f"Manual node: related words should be added directly to the instances*.json file")
            return []

    def load_tagger(self):
        """Load the appropriate spaCy model for the specified language."""
        try:
            if self.language == "ru":
                return load_spacy_model("ru_core_news_sm")
            elif self.language == "en":
                return load_spacy_model("en_core_web_sm")
            else:
                raise ValueError(f"No spaCy model specified for language: {self.language}")
        except Exception as e:
            print(f"Error loading spaCy model for language {self.language}: {e}")
            return None

    def from_conceptnet(self, word, filter_nouns=False):
        """Fetch related words from ConceptNet."""
        try:
            url = f"http://api.conceptnet.io/c/{self.language}/{word}/"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            related_words = set()
            for edge in data.get("edges", []):
                if edge.get("end", {}).get("language") == self.language:
                    related_term = edge.get("end", {}).get("label", "")
                    if self.is_valid_word(related_term, word, filter_nouns):
                        related_words.add(related_term)
                        if len(related_words) >= self.n_related_words:
                            break
            return list(related_words)
        except Exception as e:
            logger.error(f"Error fetching related words for '{word}': {e}")
            return []

    def is_valid_word(self, candidate, target, filter_nouns):
        """Check if a word is valid (not the target, not multi-word, not a function word)."""
        if candidate.lower() == target.lower() or " " in candidate or is_function_word(candidate):
            return False
        if filter_nouns and not self.is_noun(candidate):
            return False
        return True

    def is_noun(self, word):
        """Determine if a word is a noun using spaCy."""
        if not self.tagger:
            return False
        doc = self.tagger(word)
        return any(token.pos_ == "NOUN" for token in doc)

    def from_openai(self, target_word):
        """Generate related words using OpenAI."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is not set.")
        openai.api_key = self.openai_api_key
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Give me {self.n_related_words} words that are related to '{target_word}'."}
                ],
                max_tokens=50,
                temperature=0.7
            )
            raw_response = response['choices'][0]['message']['content'].strip()
            return [word.strip() for word in raw_response.split(",")[:self.n_related_words]]
        except Exception as e:
            logger.error(f"Error generating related words for '{target_word}': {e}")
            return []
