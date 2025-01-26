## Collections of games to be run with the [clembench framework](https://github.com/clp-research/clembench)

See the game specific README files for details on each game and the [framework documentation](https://github.com/clp-research/clembench/tree/main/docs) on how to run and add your own games.

### Games that still need to be updated to the new framework version:
* wordle & variants (text)
* mm_mapworld & variants (multimodal)
* chatgame (slurk)
* cloudgame (multimodal)

### HOW-TOs

#### ...run or debug `_game_/instancegenerator.py`
The script need to be able to import GameInstanceGenerator from the clembench code. 
We need to show it the path: `PYTHONPATH=/absolute/path/to/clembench`

* If you run it from the terminal: run setup_path.sh first
* If you're using PyCharm and run/debug it via GUI: Edit Configurations -> Environment Variables -> add `PYTHONPATH=/absolute/path/to/clembench`