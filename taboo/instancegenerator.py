"""The script generates game instances for the Taboo game. It selects target words and generates a list of related words.
The script uses either ConceptNet or the OpenAI API to retrieve or generate these related words.

usage:
python3 instancegenerator.py
Creates instance.json file in ./in (or instance_filename set in __main__)

"""
import os
import random
import argparse

from utils.related_words_generator import RelatedWordGenerator
from clemcore.clemgame import GameInstanceGenerator

N_INSTANCES = 20  # how many different target words
N_GUESSES = 3  # how many tries the guesser will have
N_RELATED_WORDS = 3
VERSION = "v2.0"

# Seed for reproducibility
random.seed(87326423)

# Set up OpenAI API key if using openai
OPENAI_API_KEY = ""  # Insert your OpenAI API key


class TabooGameInstanceGenerator(GameInstanceGenerator):

    def __init__(self, language):
        super().__init__(os.path.dirname(__file__))
        self.n = N_RELATED_WORDS
        self.language = language
        self.related_word_generator = RelatedWordGenerator(
            language=language, n_related_words=N_RELATED_WORDS, openai_api_key=OPENAI_API_KEY
        )

    def setup_experiment(self, frequency):
        """Sets up an experiment configuration for a specific frequency."""
        experiment = self.add_experiment(f"{frequency}_{self.language}")
        experiment["max_turns"] = N_GUESSES
        experiment["describer_initial_prompt"] = self.load_template(
            f"resources/initial_prompts/{self.language}/initial_describer"
        )
        experiment["guesser_initial_prompt"] = self.load_template(
            f"resources/initial_prompts/{self.language}/initial_guesser"
        )
        return experiment

    def on_generate(self, mode):
        # Prepare related word generation
        word_lists = self.load_json(f"resources/target_words/{self.language}/taboo_word_lists.json")

        for frequency in ["high", "medium", "low"]:
            print(f"Sampling from freq: {frequency}")

            experiment = self.setup_experiment(frequency)

            target_id = 0
            while target_id < N_INSTANCES:
                if not word_lists[frequency]:
                    print("No more words available to sample.")
                    break
                target = random.choice(word_lists[frequency])
                word_lists[frequency].remove(target)

                print(f"Retrieving related words for '{target}'")
                related_words = self.generate_related_words(target, mode)

                if len(related_words) < N_RELATED_WORDS and mode != "manual":
                    print(f"Skipping '{target}' due to lack of related words.")
                    continue

                game_instance = self.add_game_instance(experiment, target_id)
                game_instance["target_word"] = target
                game_instance["related_word"] = related_words
                target_id += 1

    def generate_related_words(self, target, mode):
        strategies = {
            "manual": self.related_word_generator.manual,
            "conceptnet": self.related_word_generator.from_conceptnet,
            "openai": self.related_word_generator.from_openai,
        }
        if mode in strategies:
            return strategies[mode](target)
        print(f"Unsupported mode: {mode}")
        return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate Taboo game instances.")
    parser.add_argument("-m", "--mode", choices=["manual", "conceptnet", "openai"], default="conceptnet",
                        help="Choose whether to use ConceptNet or OpenAI.")
    parser.add_argument("-l", "--language", default="en", help="Language for the game instances.")
    args = parser.parse_args()

    generator = TabooGameInstanceGenerator(language=args.language)

    instance_filename = f"instances_{VERSION}_{args.language}_{args.mode}.json"
    generator.generate(filename=instance_filename, mode=args.mode)
