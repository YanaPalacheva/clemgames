import requests
import openai
import logging

from taboo.utils.en.select_taboo_words import is_function_word
from taboo.utils.instance_utils import InstanceUtils

logger = logging.getLogger(__name__)

class RelatedWordGenerator:
    def __init__(self, instance_utils: InstanceUtils, language: str, n_related_words: int):
        self.instance_utils = instance_utils
        self.language = language
        self.n_related_words = n_related_words
        self.tagger = self.instance_utils.load_spacy_model()
        self.manual_related_words = {}

        self._conceptnet_endpoint = f"http://api.conceptnet.io/c/{self.language}"

        if language == 'ru':
            self.manual_related_words = self.instance_utils.load_manual_related_words()

    def manual(self, word, **kwargs):
        words = self.manual_related_words.get(word, [])
        if len(words) < self.n_related_words:
            print(f'{len(words)} related words found for word {word}! {self.n_related_words} words are expected.')
        return words

    def from_conceptnet(self, word, **kwargs):
        """Fetch related words from ConceptNet."""
        filter_nouns = kwargs.get("filter_nouns", False)
        try:
            url = f"{self._conceptnet_endpoint}/{word}/"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # this could have safety checks, like checking for the word being slang

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
        if candidate.lower() == target.lower() or (" " in candidate) or is_function_word(candidate):
            return False
        if filter_nouns and not self.is_noun(candidate):
            return False
        return True

    def is_noun(self, word):
        """Determine if a word is a noun using spaCy."""
        doc = self.tagger(word)
        return any(token.pos_ == "NOUN" for token in doc)

    def from_openai(self, target_word, **kwargs):
        """Generate related words using OpenAI."""
        openai.api_key = self.instance_utils.load_openai_api_key()
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
