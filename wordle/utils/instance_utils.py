import os

import requests
import random

from accelerate.commands.config.update import description
from clemcore.clemgame import GameResourceLocator
from .dump_categorized_words import create_word_lists


# InstanceUtils: Single point of entry combining all functionality.
class InstanceUtils:
    def __init__(self, game_path, experiment_config, game_name, language):
        self.resource_manager = ResourceManager(game_path, language, experiment_config)
        self.game_config_manager = GameConfigManager(self.resource_manager)
        self.game_name = game_name

    def select_target_words(self, populate: bool = False, use_seed: str = ""):
        # add option to populate the lists first
        if populate:
            self.resource_manager.populate_word_lists()
        # load word lists
        self.resource_manager.load_word_lists()

        seed = self.resource_manager.common_config["seed_to_select_target_word"] if not use_seed else use_seed

        return WordManager.select_target_words(self.resource_manager.easy_words,
                                                     self.resource_manager.medium_words,
                                                     self.resource_manager.hard_words,
                                                     self.resource_manager.common_config,
                                                     seed)

    def update_experiment_dict(self, experiment, lang_keywords):
        self.game_config_manager.update_experiment_dict(experiment, lang_keywords)

    def update_game_instance_dict(self, game_instance, word, difficulty):
        self.game_config_manager.update_game_instance_dict(game_instance, word, difficulty)


# ResourceManager: Handles file loading, storing, and general resource operations.
class ResourceManager(GameResourceLocator):
    def __init__(self, game_path, language, experiment_config):
        super().__init__(path=game_path)
        self.language = language
        self.experiment_config = experiment_config
        self.common_config = self.load_json("resources/common_config")
        langconfig = self.load_json("resources/langconfig")[self.language]
        self.data_sources = langconfig.pop("data_sources")
        self.resource_path = f"resources/target_words/{self.language}"

        self.official_words = []
        self.target_words = []
        self.word_clues_dict = {}
        self.easy_words = []
        self.medium_words = []
        self.hard_words = []

    def download_kaggle(self, file_config: {}):
        # Requires kaggle authentication for successfully downloading the file; see README.md
        kaggle_credentials = self.load_json("wordle_keys")['kaggle']
        os.environ['KAGGLE_USERNAME'] = kaggle_credentials['username']
        os.environ['KAGGLE_KEY'] = kaggle_credentials['key']

        if os.environ['KAGGLE_USERNAME'] == "<your-kaggle-user-name>" or os.environ['KAGGLE_KEY'] == "<kaggle-api-key>":
            print("Please provide your kaggle credentials in the instance_utils.py file\n")
            return

        description = file_config.get("description", "UNKNOWN")
        print(f"Downloading {description}...")

        dataset = file_config.get("file_url")
        filename = file_config.get("file_name")

        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(dataset, path=self.resource_path)

        # Unzip the file
        import zipfile
        zip_file_path = f"{self.resource_path}/{dataset.split('/')[-1]}.zip"
        with zipfile.ZipFile(zip_file_path,"r") as zip_ref:
            zip_ref.extractall(self.resource_path)

        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

        print(f"Stored the {description} file: {self.resource_path}/{filename}")

    def download_direct(self, file_config: {}):
        description = file_config.get("description", "UNKNOWN")
        print(f"Downloading wordle recognized words for language: {self.language}...")
        url = file_config.get("file_url")
        r = requests.get(url, allow_redirects=True)
        filename = file_config.get("file_name")
        self.store_file(r.content.decode("utf-8"), filename, self.resource_path)
        print(f"Stored {description} file", self.resource_path)

    def download_if_missing(self, file_config: {}):
        filename = file_config.get("file_name")
        file_source = file_config.get("file_source")
        # check if file exists
        file_path = os.path.join(self.resource_path, filename)
        if os.path.exists(file_path):
            return

        if self.language == 'en':
            if file_source == 'kaggle':
                self.download_kaggle(file_config)
            elif file_source == 'direct':
                self.download_direct(file_config)
            else:
                raise NotImplementedError(f'No method to download from {file_source} source!')

    def load_data(self, file_config: {}):
        # download missing sources
        self.download_if_missing(file_config)
        # read file
        return self.read_file_contents(file_config.get("file_name"))

    @staticmethod
    def custom_processing(filename, content):
        parsed_data = {}

        if "nytcrosswords.csv" in filename:
            for record in content:
                parsed_data[record[1].lower().strip()] = record[2].lower().strip()
        elif "unigram_freq.csv" in filename:
            content = content[1:]
            for word, freq in content:
                parsed_data[word.lower().strip()] = freq
        return parsed_data

    def read_file_contents(self, filename: str, file_ext: str="txt"):
        loaders = {
            'txt': self.load_file, # better to combine in one strategy-selecting method in the parent class
            'csv': self.load_csv,
            'json': self.load_json # nb: load_json also accepts filenames with no extension
        }

        file_ext = filename.split(".")[-1]
        if file_ext not in loaders.keys():
            raise ValueError(f'File {filename} extension is not supported e! Must be in {loaders.keys()}')

        try:
            content = loaders[file_ext](f"{self.resource_path}/{filename}")
        except FileNotFoundError:
            raise ValueError(f"Couldn't load {filename}.")

        # make sure content is not empty
        if not content:
            raise ValueError(f"{filename} is empty!")

        # return value (dict or list)
        parsed_data = None

        # custom clue processing (EN)
        # Crosswords Clues are list of lists, each sublist has [date, word, clue], we need word and clue
        if "nytcrosswords.csv" in filename or "unigram_freq.csv" in filename:
            parsed_data = self.custom_processing(filename, content)
        else:
            parsed_data = content.strip().split("\n")
            parsed_data = [word.lower().strip() for word in parsed_data]

        return parsed_data

    def populate_word_lists(self):
        if self.language == 'en':
            unigram_freq_file = self.data_sources.get("unigram_freq", "")
            target_words_file = self.data_sources.get("target_words", "") # not used
            clue_file = self.data_sources.get("word_clues", "")

            unigram_freq = self.load_data(unigram_freq_file)
            target_words = self.load_data(target_words_file)
            clue_words = self.load_data(clue_file)

            create_word_lists(unigram_freq=unigram_freq, target_words=target_words, clue_words=clue_words,
                              resource_path=self.resource_path)
        else:
            print(f"Word categorization method not set for language '{self.language}', skipping...")

    def load_word_lists(self):
        official_words_filename = self.data_sources.get("official_words", "")
        word_clues_filename = self.data_sources.get("word_clues", "")
        self.official_words = self.load_data(official_words_filename)
        self.word_clues_dict = self.load_data(word_clues_filename)

        # Currently the already categorized words are read directly from the files
        if "high_frequency" in self.common_config["supported_word_difficulty"]:
            self.easy_words = self.read_file_contents("easy_words.txt")
        if "medium_frequency" in self.common_config["supported_word_difficulty"]:
            self.medium_words = self.read_file_contents("medium_words.txt")
        if "low_frequency" in self.common_config["supported_word_difficulty"]:
            self.hard_words = self.read_file_contents("hard_words.txt")



# GameConfigManager: Updates experiment/game instances and prepares prompts.
class GameConfigManager:
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager

    def read_inital_prompt(self, use_clue, use_critic):
        if use_critic:
            guesser_prompt = self.resource_manager.load_template(f"resources/initial_prompts/{self.resource_manager.language}/guesser_withcritic_prompt")
            guesser_critic_prompt = self.resource_manager.load_template(f"resources/initial_prompts/{self.resource_manager.language}/critic_prompt")
        else:
            template = "guesser_withclue_prompt" if use_clue else "guesser_prompt"
            guesser_prompt = self.resource_manager.load_template(f"resources/initial_prompts/{self.resource_manager.language}/{template}")
            guesser_critic_prompt = ""

        return guesser_prompt, guesser_critic_prompt

    def update_experiment_dict(self, experiment, lang_keywords):
        experiment["common_config"] = self.resource_manager.common_config
        experiment["common_config"]["max_word_length"] = lang_keywords["max_word_length"]
        experiment["use_clue"] = self.resource_manager.experiment_config["use_clue"]
        experiment["use_critic"] = self.resource_manager.experiment_config["use_critic"]

        (
            experiment["guesser_prompt"],
            experiment["guesser_critic_prompt"],
        ) = self.read_inital_prompt(experiment["use_clue"], experiment["use_critic"])

        experiment["lang_keywords"] = lang_keywords
        experiment["lang_keywords"]["official_words_list"] = self.resource_manager.official_words

    def update_game_instance_dict(self, game_instance, word, difficulty):
        game_instance["target_word"] = word
        game_instance["target_word_clue"] = self.resource_manager.word_clues_dict[word]
        game_instance["target_word_difficulty"] = difficulty



# WordManager: Manages word categorization and selection (utility class)
class WordManager:
    @staticmethod
    def _categorize_target_words(unigram_freq_sorted_dict, clue_words_dict):
        n = len(unigram_freq_sorted_dict)
        ranges = [(0, n // 3), (n // 3, 2 * n // 3), (2 * n // 3, n)]
        clue_words_keys = set(clue_words_dict.keys())

        def filter_words(start, end):
            return list(set(word[0] for word in unigram_freq_sorted_dict[start:end]).intersection(clue_words_keys))

        easy_words_list, medium_words_list, hard_words_list = (filter_words(start, end) for start, end in ranges)

        return easy_words_list, medium_words_list, hard_words_list

    @staticmethod
    def get_target_word_freq(word_list, freq_dict):
        return {word: freq_dict[word] for word in word_list if word in freq_dict}

    @staticmethod
    def select_target_words(easy_words: [], medium_words: [], hard_words: [],
                            config: dict, seed: str):
        number_of_target_words = config["number_of_target_words"]

        target_words = {}

        for difficulty, words_list in [("high_frequency", easy_words),
                                       ("medium_frequency", medium_words),
                                       ("low_frequency", hard_words)]:

            if difficulty in config["supported_word_difficulty"]:
                random.seed(seed)
                target_words[difficulty] = random.choices(words_list, k=number_of_target_words[difficulty])

        return target_words
