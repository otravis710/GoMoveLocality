#---------------------------------------------------------------------
# distance.py
# Owen Travis
# For reading SGF files, identifying suspected robots, and calculating
# the distance between successive moves
#---------------------------------------------------------------------

# Import functions from Sgfmill and Sgfmillplus
from sgfmillplus import get_root, is_go, has_multiple_moves, get_player_names, get_player_ranks
from sgfmillplus import playernames_contain_substrings
from sgfmill import common
# Import libraries
import numpy as np
import os
import random
import pandas as pd

# List of substrings for identifying robots. Additional robots are later
# flagged in data processing (see: distance.rmd).
BOT_PARTIALS = {"kata", "zen", "petgo", "gnugo", "gomancer", "nexus",
"neural", "sgmdb", "alphacent1", "dcnn", "golois", "bot", "tw001", "pachipachi", "alphago"}

# Advance past the handicap stones (handicap stones may or may not be
# recorded as actual moves in the SGF file).
def skipHandicap(root):
    curr = root[0]
    # If there is a handicap and the first two moves were played by the
    # same color, then we must advance the game past these moves.
    if root.has_property("HA") and curr.get_move()[0] == curr[0].get_move()[0]:
        handicap = root.get("HA")
        try:
            for _ in range(handicap):
                curr = curr[0]
        except:
            return None
    return curr

# Given the root node of an Sgf_game object, return a data frame
# with information about each move, including the distance to the
# previous move.
def process_game(root):
    ranks = get_player_ranks(root)
    names = get_player_names(root)
    bot_status = playernames_contain_substrings(root, BOT_PARTIALS)

    rows = []

    moveNumber = 1
    prev_sgf_vertex = None

    # Skip past the handicap moves, if they are played out
    curr = skipHandicap(root)
    if not curr:
        return pd.DataFrame(rows, columns=["num", "color", "playerName", "playerRank", "isBot", "gtp_vertex", "played_dx", "played_dy", "prev_gtp_vertex"])

    while True:
        color, sgf_vertex = curr.get_move()
        if sgf_vertex and prev_sgf_vertex:
                played_dx = int(abs(sgf_vertex[1]-prev_sgf_vertex[1]))
                played_dy = int(abs(sgf_vertex[0]-prev_sgf_vertex[0]))
        else:
            played_dx = None
            played_dy = None
        row = [moveNumber,
               color,
               names[color],
               ranks[color],
               bot_status[color],
               common.format_vertex(sgf_vertex),
               played_dx,
               played_dy,
               common.format_vertex(prev_sgf_vertex)]
        rows.append(row)

        # Exit the loop if there are no more moves in the game
        if len(curr) == 0:
            break

        # If the current move was not a "pass", update the previous move
        if sgf_vertex:
            prev_sgf_vertex = sgf_vertex
        
        # Advance the loop
        curr = curr[0]
        moveNumber += 1

    # Edge case: the first move of the game
    rows[0][-1] = None

    return pd.DataFrame(rows, columns=["num", "color", "playerName", "playerRank", "isBot", "gtp_vertex", "played_dx", "played_dy", "prev_gtp_vertex"])


# Given a data folder and filenames, call process_game() for each game.
# If isAlphaGoSelfPlay, skip checking if the game is valid.
# Return one concatenated data frame for all moves in all games.
def process_all_games(data_folder, filenames, isAlphaGoSelfPlay=False):
    dfs = []
    count = 0
    for filename in filenames:
        filepath = os.path.join(data_folder, filename.strip())

        # Get the root of the file
        try:
            root = get_root(filepath)
        except:
            print("Quitting. Not a valid sgf file.")
            continue

        # Check that the game is valid
        if not (isAlphaGoSelfPlay or is_go(root)):
            print("Quitting. Game not identified as Go.")
            continue
        if not (isAlphaGoSelfPlay or has_multiple_moves(root)):
            print("Quitting. Game has fewer than two moves.")
            continue
        print("Root is valid.")

        # Process the game
        game_df = process_game(root)
        game_df["gameFile"] = filename.strip()
        dfs.append(game_df)

        # Increment the count
        count += 1

    return pd.concat(dfs, ignore_index=True, axis=0)

# Process all human games and AlphaGo games.
def main():
    human_data_folder = '/path/to/human/data/folder'
    with open(os.path.join(human_data_folder, "gamesList.txt"), "r") as gamesList:
        human_filenames = gamesList.readlines()
    human_df = process_all_games(human_data_folder, human_filenames)
        
    alphago_data_folder = '/path/to/alphago/data/folder'
    with open(os.path.join(alphago_data_folder, "agGamesList.txt"), "r") as agGamesList:
        alphago_filenames = agGamesList.readlines()
    ag_df = process_all_games(alphago_data_folder, alphago_filenames, True)

    ag_df["isAlphaGo"] = 1
    human_df["isAlphaGo"] = 0

    res = pd.concat([ag_df, human_df], ignore_index=True, axis=0)
    res.to_csv("distance_output.csv", index=False)

if __name__=="__main__":
    main()