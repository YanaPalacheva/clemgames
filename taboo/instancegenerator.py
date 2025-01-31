"""The script generates game instances for the Taboo game. It selects target words and generates a list of related words.
The script uses either ConceptNet or the OpenAI API to retrieve or generate these related words.

usage:
python3 instancegenerator.py
Creates instance.json file in ./in (or instance_filename set in __main__)

"""
import os
import random
import argparse
import nltk

from utils.related_words_generator import RelatedWordGenerator
from taboo.utils.instance_utils import InstanceUtils
from clemcore.clemgame import GameInstanceGenerator


VERSION = "v2.0"

# Seed for reproducibility
# random.seed(87326423)  # v1 seed


class TabooGameInstanceGenerator(GameInstanceGenerator):

    def __init__(self, language):
        super().__init__(os.path.dirname(__file__))
        self.language = language
        self.instance_utils = InstanceUtils(language=language,
                                            game_path=os.path.dirname(os.path.abspath(__file__)))
        self.prompt_path = f"resources/initial_prompts/{self.language}/"
        self.wordlist_path = f"{self.instance_utils.resource_path}/taboo_word_lists.json"
        self.common_config = self.load_json("resources/common_config.json")
        self.related_word_generator = RelatedWordGenerator(instance_utils=self.instance_utils,
                                                           language=language,
                                                           n_related_words=self.common_config.get("N_RELATED_WORDS"))

    def setup_experiment(self, frequency):
        """Sets up an experiment configuration for a specific frequency."""
        experiment = self.add_experiment(f"{frequency}_{self.language}")
        experiment["max_turns"] = self.common_config.get("N_GUESSES")
        experiment["describer_initial_prompt"] = self.load_template(f"{self.prompt_path}/initial_describer")
        experiment["guesser_initial_prompt"] = self.load_template(f"{self.prompt_path}/initial_guesser")
        return experiment

    def on_generate(self, mode: str):
        random.seed(self.common_config.get("SEED"))
        word_lists = self.load_json(self.wordlist_path)

        for frequency in self.common_config.get("supported_word_frequency"):
            print(f"Sampling from freq: {frequency}")
            experiment = self.setup_experiment(frequency)

            target_id = 0
            while target_id < self.common_config.get("N_INSTANCES"):
                if not word_lists.get(frequency):
                    print("No more words available to sample.")
                    break

                target = random.choice(word_lists[frequency])
                word_lists[frequency].remove(target)

                # only use words of length 3 or greater
                if len(target) < 3:
                    continue

                print(f"Retrieving related words for '{target}'...")
                related_words = self.get_related_words(target, mode, filter_nouns=False)

                if len(related_words) < self.common_config.get("N_RELATED_WORDS") and mode != "manual":
                    print(f"Skipping '{target}' due to lack of related words.")
                    continue

                # stem words: nltk SnowballStemmer is not reliable - manual inspection and correction still needed!
                stemmer = self.instance_utils.get_stemmer()
                target_word_stem = stemmer.stem(target)
                related_word_stem = [stemmer.stem(related_word) for related_word in related_words]

                # add a valid game instance
                game_instance = self.add_game_instance(experiment, target_id)
                game_instance["target_word"] = target
                game_instance["related_word"] = related_words
                game_instance["target_word_stem"] = target_word_stem
                game_instance["related_word_stem"] = related_word_stem
                game_instance['lang'] = self.language

                target_id += 1

    def get_related_words(self, target, mode, **kwargs):
        generators = {
            "manual": self.related_word_generator.manual,
            "conceptnet": self.related_word_generator.from_conceptnet,
            "openai": self.related_word_generator.from_openai,
        }
        if mode in generators:
            return generators[mode](target, **kwargs)
        else:
            print(f"Unsupported mode for related words: {mode}")
            return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate Taboo game instances.")
    parser.add_argument("-m", "--mode", choices=["manual", "conceptnet", "openai"], default="conceptnet",
                        help="Method to generate related words.")
    parser.add_argument("-l", "--language", default="en", help="Language for the game instances.")
    args = parser.parse_args()

    generator = TabooGameInstanceGenerator(language=args.language)

    instance_filename = f"instances_{VERSION}_{args.language}_{args.mode}.json"
    generator.generate(filename=instance_filename, mode=args.mode)
