import json
from typing import Dict, List
from pathlib import Path

import pandas as pd
from ruwordnet import RuWordNet

wn = RuWordNet()  # run "ruwordnet download" in the terminal to load the database (~80mB)

resource_dir = Path(__file__).resolve().parents[2] / "resources" / "target_words" / "ru"
OUTPUT_FILENAME = resource_dir / "related_words.json"


def valid_candidate(candidate: str, word: str) -> bool:
    if len(candidate.split(' ')) == 1:
        if word not in candidate:
            return True
    return False


def extract_related_words(words: pd.Series) -> Dict[str, List]:
    related_words = {}
    for word in words:
        related = set()
        for ss in wn.get_synsets(word):
            for candidate in ss.title.split(', '):
                if valid_candidate(candidate.lower(), word):
                    related.add(candidate.lower())

            for hn in ss.meronyms:
                for candidate in hn.title.split(', '):
                    if valid_candidate(candidate.lower(), word):
                        related.add(candidate.lower())

        if len(related) >= 3:
            related = [word.strip(')') for word in related] # WordNet artifact
            related_words[word] = list(related)

    with open(OUTPUT_FILENAME, 'w') as json_file:
        json.dump(related_words, json_file, indent=4)

    return related_words
