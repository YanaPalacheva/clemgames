import json
from pathlib import Path

from libretranslatepy import LibreTranslateAPI

ALIGN_PROMPTS = True  # leave original prompts or replace them with the target language
LANGUAGE = 'ru'

# Initialize the LibreTranslate API
translator = LibreTranslateAPI("https://translate.flossboxin.org.in/")  # if doesn't work - check here https://github.com/LibreTranslate/LibreTranslate#mirrors

# Function to translate text into target language
def translate_to_target(text, source='en'):
    try:
        # Use LibreTranslate API to translate the text
        return translator.translate(text, source=source, target=LANGUAGE)
    except Exception as e:
        print(f"Error translating '{text}': {e}")
        return text  # Return the original text if translation fails

# Point to JSON files
in_dir = Path(__file__).resolve().parents[2] / "in"
input_file_path = in_dir / 'instances_v1.6_en_manual.json'
output_file_path = in_dir / f'instances_v1.6_{LANGUAGE}_manual_translated.json'

# Target prompts
prompt_dir = Path(__file__).resolve().parents[2] / "resources" / "initial_prompts" / LANGUAGE

with open(input_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Process each experiment and translate target_word and related_word
for experiment in data['experiments']:
    for instance in experiment['game_instances']:
        # Translate target_word
        instance['target_word'] = translate_to_target(instance['target_word'])

        # Translate each related_word
        instance['related_word'] = [translate_to_target(word) for word in instance['related_word']]

        # Remove target_word_stem and related_word_stem
        instance.pop('target_word_stem', None)
        instance.pop('related_word_stem', None)

    if ALIGN_PROMPTS:
        experiment["describer_initial_prompt"] = (prompt_dir / "initial_describer.template").read_text(encoding="utf-8")
        experiment["guesser_initial_prompt"] = (prompt_dir / "initial_guesser.template").read_text(encoding="utf-8")

# Save the translated JSON file
with open(output_file_path, 'w', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

print(f"Translation completed. Translated file saved to {output_file_path}")
