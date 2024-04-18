#---------------------------------------------------------------------
# accuracy.py
# Owen Travis
# For reading SGF files, identifying suspected robots, spawning sub-
# processes running KataGo, and determining the optimal move in each
# position. The core logic of this code is rooted in files written for
# our previous work (see Travis et al. 2023).
#---------------------------------------------------------------------

# Import functions from Sgfmill and Sgfmillplus
from sgfmillplus import get_root, is_go, has_multiple_moves, get_player_names, get_player_ranks
from sgfmillplus import get_time_system, get_overtime_system, get_game_result, playernames_contain_substrings
from sgfmill import common

# Import libraries
import os
import subprocess
import pandas as pd

# Number of jobs (if using a job array on the cluster)
NUMJOBS = 300

# Paths to other files
KATAGO = "/path/to/KataGo/executable"
MODEL = "/path/to/KataGo/model/g170-b30c320x2-s4824661760-d1229536699.bin.gz"
CFG_FILE = "/path/to/gtp/cfg/file"

# List of substrings for identifying robots. Additional robots are later
# flagged in data processing (see: accuracy.rmd).
BOT_PARTIALS = {"kata", "zen", "petgo", "gnugo", "gomancer", "nexus",
"neural", "sgmdb", "alphacent1", "dcnn", "golois", "bot", "tw001", "pachipachi"}

# Class storing data about each move.
# I should change this to a namedtuple.
class MoveInfo:
    def __init__(self,
                 num,
                 color,
                 gtp_vertex,
                 in_overtime,
                 playerName,
                 gameFile,
                 playerRank,
                 timeSystem,
                 overtimeSystem,
                 gameResult):
        self.num = num
        self.color = color
        self.gtp_vertex = gtp_vertex
        self.in_overtime = in_overtime
        self.playerName = playerName
        self.gameFile = gameFile
        self.playerRank = playerRank
        self.timeSystem = timeSystem
        self.overtimeSystem = overtimeSystem
        self.gameResult = gameResult
        self.played_dx = None
        self.played_dy = None
        self.analyzed = None
        self.bestMove = None
        self.prev_gtp_vertex = None
        self.best_dx = None
        self.best_dy = None
        self.isBot = None

    def __str__(self):
        res = f"{self.num:<3} {self.color:<1}"
        res = res +  f" {self.gtp_vertex:<4} {self.in_overtime:<2} "
        res += f"{self.played_dx} "
        res += f"{self.played_dy} "
        res += str(self.analyzed) + " "
        res += str(self.bestMove) + " "
        res += str(self.prev_gtp_vertex) + " "
        return res

# Spawn a subprocess running KataGo and feed it kata_input
def runkata(kata_input, cfg_file, output_file):
    cmd = []
    cmd.append(KATAGO)
    cmd.append("gtp")
    cmd.append("-model")
    cmd.append(MODEL)
    cmd.append("-config")
    cmd.append(cfg_file)
    with subprocess.Popen(cmd, text=True,
    stderr=subprocess.PIPE, stdin=subprocess.PIPE, stdout=output_file) as proc:
        # wait for setup
        while True:
            errLine = proc.stderr.readline()
            if "GTP ready" in errLine:
                break
        # play out the game
        proc.communicate(kata_input)

# Advance past the handicap stones, which may or may not be recorded
# as moves in the sgf file.
def handle_handicap(root, curr):
    if root.has_property("HA") and curr.get_move()[0] == curr[0].get_move()[0]:
        # Handicap exists and is played out
        print("Handicap is played out")
        handicap = root.get("HA")
        for _ in range(handicap):
            curr = curr[0]
    else:
        # Handicap is not played out in sgf, or there is no handicap
        print("Handicap is not played out")
        handicap = 0
    return handicap, curr

# Generate KataGo input to be passed to runkata
def get_katago_input(root, filepath, data_folder, allMovesL, whiteIsBot, blackIsBot):
    kata_list = []
    curr = root[0]

    # Advance past the handicap moves
    try:
        handicap, curr = handle_handicap(root, curr)
    except Exception as e:
        print(e)
        return False
    
    # KataGo input: load game file past the handicap and eliminate time settings.
    kata_list.append(" ".join(["loadsgf", os.path.join(data_folder, filepath), str(handicap + 1)]))
    kata_list.append("kata-time_settings none")

    # Track move count
    count = 1

    bots = set()
    if whiteIsBot:
        bots.add('w')
    if blackIsBot:
        bots.add('b')

    player_names = get_player_names(root)
    player_ranks = get_player_ranks(root)
    time_system = get_time_system(root)
    overtime_system = get_overtime_system(root)
    game_result = get_game_result(root)

    prev_sgf_vertex = None

    # Iterate through each move of the game
    while True:
        color, sgf_vertex = curr.get_move()
        gtp_vertex = common.format_vertex(sgf_vertex)

        moveO = MoveInfo(count,
                         color,
                         gtp_vertex,
                         in_overtime=curr.has_property("O" + color.upper()),
                         playerName = player_names[color],
                         gameFile = filepath,
                         playerRank = player_ranks[color],
                         timeSystem = time_system,
                         overtimeSystem = overtime_system,
                         gameResult = game_result
                         )

        moveO.prev_gtp_vertex = common.format_vertex(prev_sgf_vertex)
        if prev_sgf_vertex and sgf_vertex:
            moveO.played_dx = int(abs(sgf_vertex[1]-prev_sgf_vertex[1]))
            moveO.played_dy = int(abs(sgf_vertex[0]-prev_sgf_vertex[0]))

        moveO.isBot = color in bots

        if color in bots or not prev_sgf_vertex:
            moveO.analyzed = False
        # If this is a human move, analyze the optimal move.
        else:
            moveO.analyzed = True
            kata_list.append("clear_cache")
            kata_list.append("kata-genmove_analyze " + color + " maxmoves 3")
            kata_list.append("undo")
    
        allMovesL.append(moveO)
        kata_list.append(" ".join(["play", color, gtp_vertex]))

        # Exit the loop if there are no more moves in the game
        if len(curr) == 0:
            break
        
        # If the current move was not a "pass", update the previous move
        if sgf_vertex:
            prev_sgf_vertex = sgf_vertex

        # Advance the loop
        curr = curr[0]
        count += 1
    
    return "\n".join(kata_list) + "\n"        

# Process KataGo output and extract the optimal moves
def readOutput(allMovesL, outputF):
    index = 0
    for line in outputF:
        if line.startswith("play"):
            while not allMovesL[index].analyzed:
                index += 1
            moveO = allMovesL[index]
            moveO.bestMove = line.split()[-1]

            index += 1

# Compute Manhattan distances from each move to the previous move
def addDistancesToMoveO(moveO):
    bestMoveSGF = common.move_from_vertex(moveO.bestMove, 19)
    prevVertexSGF = common.move_from_vertex(moveO.prev_gtp_vertex, 19)
    if bestMoveSGF and prevVertexSGF:
        moveO.best_dx = int(abs(bestMoveSGF[1] - prevVertexSGF[1]))
        moveO.best_dy = int(abs(bestMoveSGF[0] - prevVertexSGF[0]))

# Validate each game file, generate KataGo input, run KataGo,
# and process KataGo output.
def main_helper(filepath, data_folder, dfs):
    allMovesL = []
    print(f"Loading file {filepath}.")

    # Get the root of the Sgf_game object
    try:
        root = get_root(os.path.join(data_folder, filepath))
    except:
        print("Quitting. Not a valid sgf file.")
        return
    
    # Check that the game is valid
    if not is_go(root):
        print("Quitting. Game not identified as Go.")
        return
    if not has_multiple_moves(root):
        print("Quitting. Game has fewer than two moves.")
        return
    print("Root is valid.")
    
    # Identify robots
    bot_status = playernames_contain_substrings(root, BOT_PARTIALS)
    if bot_status["b"] and bot_status["w"]:
        print("Quitting. Found two bots.")
        return
    
    # Generate KataGo input
    katago_input = get_katago_input(root, filepath, data_folder, allMovesL, bot_status["w"], bot_status["b"])
    if not katago_input:
        print("Quitting. Issue generating katago input.")
        return
    output_filepath = "/file/for/saving/KataGo/output"

    # Run KataGo
    print("Saving to " + str(output_filepath))
    print("Running katago.")
    with open(output_filepath, "w+") as outputF:
        runkata(katago_input, CFG_FILE, outputF)
    print("Saved output to: " + output_filepath)

    # Read KataGo output
    with open(output_filepath, "r") as outputF:
        readOutput(allMovesL, outputF)

    # Calculate distances
    for moveO in allMovesL:
        if moveO.analyzed:
            addDistancesToMoveO(moveO)

    # Edge case: the first move of the game
    allMovesL[0].prev_gtp_vertex = None

    dfs.append(pd.DataFrame([vars(s) for s in allMovesL]))
    
# Given a data folder 
def main():
    dfs = []

    # Set to False if running a non-array cluster job
    is_array_job = True
    # Set to False if testing on local machine
    on_cluster = True

    if is_array_job:
        job_idx = int(os.environ["SLURM_ARRAY_TASK_ID"]) - 1
    else:
        job_idx = -1

    if on_cluster:
        data_folder = '/path/to/data/folder/on/cluster'
    else:
        data_folder = '/path/to/data/folder/on/local/machine'

    with open(os.path.join(data_folder, "gamesList.txt"), "r") as gamesList:
        filenames = gamesList.readlines()

    # Divide the game files among NUMJOBS jobs
    for i in range(len(filenames)):
        if i % NUMJOBS == job_idx or job_idx == -1:
            main_helper(filenames[i].strip(), data_folder, dfs)
        

    if on_cluster:
        pd.concat(dfs, ignore_index=True).to_csv(f'/path/to/output/folder/{job_idx}.csv')
    else:
        pd.concat(dfs, ignore_index=True).to_csv('/path/to/output/file.csv')

if __name__ == "__main__":
    main()