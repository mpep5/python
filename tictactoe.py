#!/usr/bin/env python3
"""Tic-tac-toe: watch the computer learn, or play against it.

Author: Mike Pepe
Originally completed many years ago
reproduced from scratch June 2022
updated to learn from games September 2026
cleaned up and extended with Player-vs-Computer, Training and Competition modes

Modes
-----
D  Display  Computer vs computer. Draws the board after every move and
            announces each result, pausing so a human can follow along.
            Both sides play the best moves the computer has learned so far
            (random play if there is no history yet). Nothing is learned
            or saved in this mode.
T  Training The computer plays itself, silently and fast, and learns from
            every game. Each game is appended to the history file, and the
            history is read back at startup, so experience carries over
            between runs. Improvement and perfect play are not guaranteed.
            Randomness is deliberate here (a few random moves, random choice
            among equally good moves) so it keeps
            discovering new things. Prints results by stage of training, and
            how the computer does against a random opponent before vs after.
C  Compete  Computer vs computer with no randomness at all, to show what the
            history buys. Nothing is learned or saved. "History" contestants
            always play the best move the history knows (the lowest square
            number breaks ties); "no history" contestants use an empty brain,
            which in practice means always taking the lowest open square.
            Shows two things: (1) every possible game against each
            contestant, as X and as O, counted as won/lost/tied (the
            contestant makes its one best move each turn while the opponent
            tries every possible move, so the counts are exact), and (2) the
            four head-to-head pairings, one fixed game each.
B  Best     Analyzes the history to find the best opening. For each of the
            nine first-move squares, shows how many games started there, how
            they ended, and a score (win = 1, tie = 0.5, loss = 0), ranked
            best-first, plus a summary for center / corners / edges. Then
            shows O's best reply to each first move, scored the same way
            from O's side. Nothing is learned or saved.
P  Player  You vs the computer. You choose squares 1-9. The computer takes a
            winning move if it has one, blocks yours if you have one, and
            otherwise picks a random open square. Before each game you
            choose whether to go first (as X) or second (as O). This mode
            does not use the trained brain or save games.

Board representation
--------------------
The board is a flat list of 9 squares, read left-to-right, top-to-bottom,
starting in the top-left corner. Each square holds EMPTY (0), X (1) or O (2).

    index:  0 | 1 | 2        what you type in Player mode:  1 | 2 | 3
            ---------                                       ---------
            3 | 4 | 5                                       4 | 5 | 6
            ---------                                       ---------
            6 | 7 | 8                                       7 | 8 | 9

Players
-------
A "player" is any function ``f(board, mark) -> square_index``. The game loop
does not know or care whether a human or the computer is behind it, so new
kinds of player only need a new function with that signature.

How the computer learns
-----------------------
The history file has one finished game per line: the squares played, in
order (0-8), then the result (X, O or T for a tie), for example::

    7,8,5,4,1,2,6,3,0,T

Every board position along the way can be rebuilt from that line, so nothing
else needs to be stored. When a game is learned, each move is scored from the
point of view of the player who made it: 1 for a win, 0.5 for a tie, 0 for a
loss. The "brain" keeps, for every (board position, square chosen) pair, the
average score over all games seen. To move, the learning player picks the
open square with the best average. Squares it has no experience with count
as a 0.5 (a coin flip), so untried moves are preferred over moves known to
lose but not over moves known to win. While training it also plays a random
move a small fraction of the time (EXPLORE_RATE), so it keeps discovering
moves it hasn't tried.

Usage
-----
Interactive (prompts for anything not given on the command line)::

    $ ./tictactoe.py

Non-interactive::

    $ ./tictactoe.py --mode T --games 100000
    $ ./tictactoe.py --mode T --games 20000 --history /tmp/trial.txt
    $ ./tictactoe.py --mode C                           # what history buys
    $ ./tictactoe.py --mode B                           # best opening
    $ ./tictactoe.py --mode D --games 1 --pause 0.5
    $ ./tictactoe.py --mode P --games 3
    $ ./tictactoe.py --mode T --games 1000 --seed 42    # repeatable

The history file defaults to ``history.txt`` next to this script. To start
learning from scratch, delete it (or point --history at a new file).

Design notes
------------
Board logic and the brain do not print; ``play_game`` returns who won and
the moves played, and the session runners tally results. Random players use
Python's shared random generator. Printing and sleeping live in presentation
helpers, prompts (including the human player), and session runners.
"""

import argparse
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

#
# Constants
#
EMPTY, X, O = 0, 1, 2

# Characters used when drawing each kind of square.
SYMBOLS = {EMPTY: "-", X: "X", O: "O"}

# The eight ways to win: three rows, three columns, two diagonals.
WIN_LINES = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # columns
    (0, 4, 8), (2, 4, 6),              # diagonals
)

MODE_DISPLAY, MODE_TRAIN, MODE_COMPETE, MODE_BEST, MODE_PLAYER = "D", "T", "C", "B", "P"

def _make_symmetries():
    """Return the 8 ways to rotate/mirror the board, as tuples where
    ``perm[square]`` is where `square` ends up."""
    def rotate(square):
        row, col = divmod(square, 3)
        return col * 3 + (2 - row)

    def mirror(square):
        row, col = divmod(square, 3)
        return row * 3 + (2 - col)

    perms = []
    perm = list(range(9))
    for _ in range(4):
        perms.append(tuple(perm))
        perms.append(tuple(mirror(square) for square in perm))
        perm = [rotate(square) for square in perm]
    return tuple(perms)


# Board symmetries: positions related by these are strategically identical.
SYMMETRIES = _make_symmetries()

# Kinds of opening square, for grouping in the best-first-move analysis.
SQUARE_KINDS = (
    ("Center", (4,)),
    ("Corners", (0, 2, 6, 8)),
    ("Edges", (1, 3, 5, 7)),
)

# History file: result codes, and where it lives by default.
RESULT_CODES = {"X": X, "O": O, "T": EMPTY}
RESULT_LETTERS = {winner: letter for letter, winner in RESULT_CODES.items()}
DEFAULT_HISTORY = Path(__file__).resolve().with_name("history.txt")

# Learning parameters.
EXPLORE_RATE = 0.10     # chance per move of a random move while training
PRIOR_WEIGHT = 1        # how many "coin flip" games an unseen move starts with
BENCHMARK_GAMES = 2000  # games per side when measuring against a random player
TREND_STAGES = 5        # how many stages to split a training run into
MIN_REPLY_GAMES = 50    # fewest games for a reply to count in the best-reply analysis


#
# Game logic (board state is local to each game)
#
def new_board():
    """Return a fresh board: nine empty squares."""
    return [EMPTY] * 9


def open_squares(board):
    """Return the indexes (0-8) of every empty square on the board."""
    return [i for i, mark in enumerate(board) if mark == EMPTY]


def other(mark):
    """Return the opposing mark: X -> O and O -> X."""
    return 3 - mark


def find_winner(board):
    """Return X or O if that mark has three in a row, otherwise EMPTY."""
    for a, b, c in WIN_LINES:
        if board[a] == board[b] == board[c] != EMPTY:
            return board[a]
    return EMPTY


def play_game(players, on_move=None):
    """Play one complete game and return the winner and the moves played.

    X always moves first, and the marks alternate until someone gets three
    in a row or the board is full.

    Args:
        players: dict mapping X and O to player functions
                 ``f(board, mark) -> square_index``.
        on_move: optional callback ``f(board)`` called with the starting
                 board and again after every move (used for drawing).

    Returns:
        ``(winner, moves)``: winner is X or O, or EMPTY for a tie ("the
        cat"); moves is the list of square indexes played, in order.
    """
    board = new_board()
    moves = []
    if on_move:
        on_move(board)
    mark = X
    for move in range(1, 10):
        square = players[mark](board, mark)
        board[square] = mark
        moves.append(square)
        if on_move:
            on_move(board)
        # Nobody can have three in a row before the 5th move overall.
        if move >= 5 and find_winner(board) != EMPTY:
            return mark, moves
        mark = other(mark)
    return EMPTY, moves


#
# The brain: what the computer has learned
#
class Brain:
    """Average results of every (board position, move) seen in past games.

    Attributes:
        stats: dict mapping ``(board_tuple, square)`` to ``[total, count]``,
               where total is the summed score (1 win, 0.5 tie, 0 loss, from
               the point of view of the player who made the move) and count
               is how many games it was played in.
        openings: dict mapping each first move (0-8, always X's) to a Counter
               of how those games ended (keys X, O, EMPTY).
        replies: dict mapping ``(first_move, reply)`` (X's first move and
               O's answer to it) to a Counter of how those games ended.
        games: how many games have been learned.
    """

    def __init__(self):
        self.stats = {}
        self.openings = {}
        self.replies = {}
        self.games = 0

    def learn(self, moves, winner):
        """Learn from one finished game.

        Replays `moves` from an empty board and credits each move with the
        game's result from the mover's point of view.
        """
        board = new_board()
        mark = X
        for square in moves:
            if winner == EMPTY:
                reward = 0.5
            else:
                reward = 1.0 if winner == mark else 0.0
            entry = self.stats.setdefault((tuple(board), square), [0.0, 0])
            entry[0] += reward
            entry[1] += 1
            board[square] = mark
            mark = other(mark)
        self.openings.setdefault(moves[0], Counter())[winner] += 1
        if len(moves) > 1:
            self.replies.setdefault((moves[0], moves[1]), Counter())[winner] += 1
        self.games += 1

    def score(self, position, square):
        """Return the expected result (0 to 1) of playing `square` in `position`.

        `position` is the board as a tuple. Unseen moves score 0.5, and
        experience gradually outweighs that starting guess.
        """
        total, count = self.stats.get((position, square), (0.0, 0))
        return (total + PRIOR_WEIGHT * 0.5) / (count + PRIOR_WEIGHT)


#
# Players
#
def random_player(board, mark):
    """Computer player: pick any open square at random."""
    return random.choice(open_squares(board))


def make_learning_player(brain, explore=0.0, deterministic=False):
    """Return a player function that plays the best moves `brain` knows.

    Args:
        brain:         the Brain to consult.
        explore:       chance (0 to 1) on each move of playing a random open
                       square instead, so new moves get tried while training.
                       Use 0 to play the best known move every time.
        deterministic: if True, equally-scored best moves are settled by
                       taking the lowest square number instead of at random,
                       so the same position always gets the same move.

    By default, equally-scored best moves are chosen between at random. With
    an empty brain every move scores the same, so it plays randomly (or, if
    deterministic, always takes the lowest open square).
    """
    def learning_player(board, mark):
        squares = open_squares(board)
        if explore and random.random() < explore:
            return random.choice(squares)
        position = tuple(board)
        scored = [(brain.score(position, square), square) for square in squares]
        best = max(score for score, _ in scored)
        candidates = [square for score, square in scored if score == best]
        return candidates[0] if deterministic else random.choice(candidates)
    return learning_player


def winning_square(board, mark):
    """Return a square where `mark` would win on its next move, else None.

    Tries each open square in turn (undoing the trial move afterwards, so
    the board is left unchanged).
    """
    for square in open_squares(board):
        board[square] = mark
        won = find_winner(board) == mark
        board[square] = EMPTY
        if won:
            return square
    return None


def smart_player(board, mark):
    """Computer player: win if possible, else block, else play randomly.

    1. If it can complete three in a row, it does.
    2. Otherwise, if the opponent could win next move, it takes that square.
    3. Otherwise it picks a random open square.

    This is beatable (it doesn't set up or stop forks), but it never misses
    an immediate win or an immediate loss.
    """
    for target in (mark, other(mark)):
        square = winning_square(board, target)
        if square is not None:
            return square
    return random_player(board, mark)


def human_player(board, mark):
    """Human player: ask at the keyboard for a square from 1 to 9.

    Keeps asking until the entry is a number from 1-9 naming an empty
    square. Returns the board index (0-8). EOFError (Ctrl-D) and
    KeyboardInterrupt (Ctrl-C) are left for the caller to handle.
    """
    while True:
        entry = input(f"Your move ({SYMBOLS[mark]}), pick a square 1-9: ").strip()
        try:
            square = int(entry) - 1
        except ValueError:
            print("Please enter a number from 1 to 9.")
            continue
        if not 0 <= square < 9:
            print("Please enter a number from 1 to 9.")
        elif board[square] != EMPTY:
            print("That square is taken.")
        else:
            return square


#
# History file
#
def format_game(moves, winner):
    """Return one history-file line (no newline) for a finished game.

    Example: ``format_game([7, 8, 5, 4, 1, 2, 6, 3, 0], EMPTY)`` returns
    ``"7,8,5,4,1,2,6,3,0,T"``.
    """
    return ",".join(str(square) for square in moves) + "," + RESULT_LETTERS[winner]


def parse_game(line):
    """Parse one history-file line into ``(moves, winner)``.

    The line is replayed to make sure it describes a real, finished game
    whose stated result matches its moves.

    Raises:
        ValueError: if the line is malformed, has an illegal move, has moves
                    after the game was already over, is unfinished, or names
                    the wrong result.
    """
    *move_tokens, result = line.strip().split(",")
    moves = [int(token) for token in move_tokens]
    board = new_board()
    mark = X
    for index, square in enumerate(moves):
        if not 0 <= square <= 8 or board[square] != EMPTY:
            raise ValueError(f"illegal move {square}")
        board[square] = mark
        mark = other(mark)
        if find_winner(board) != EMPTY and index != len(moves) - 1:
            raise ValueError("moves continue after the game was won")
    winner = find_winner(board)
    if winner == EMPTY and len(moves) != 9:
        raise ValueError("game is unfinished")
    if RESULT_CODES.get(result) != winner:
        raise ValueError("stated result does not match the moves")
    return moves, winner


def load_brain(path):
    """Build a Brain from the history file at `path`.

    A missing file just gives an empty brain. Blank lines are ignored;
    unreadable lines are skipped and counted.

    Returns:
        ``(brain, skipped)``: the Brain, and the number of lines skipped.
    """
    brain = Brain()
    skipped = 0
    try:
        with open(path) as history:
            for line in history:
                if not line.strip():
                    continue
                try:
                    moves, winner = parse_game(line)
                except ValueError:
                    skipped += 1
                    continue
                brain.learn(moves, winner)
    except FileNotFoundError:
        pass
    return brain, skipped


#
# Presentation
#
def format_board(board, numbered=False):
    """Return the board as a printable, three-line string.

    Args:
        board:    list of 9 squares.
        numbered: if True, empty squares show their 1-9 number (so a human
                  knows what to type) instead of '-'.
    """
    cells = [
        str(i + 1) if numbered and mark == EMPTY else SYMBOLS[mark]
        for i, mark in enumerate(board)
    ]
    return "\n".join("|".join(cells[row:row + 3]) for row in (0, 3, 6))


def announce_result(winner, names, pause=0.0):
    """Print who won ("the Cat" for a tie), then wait `pause` seconds.

    Args:
        winner: X, O or EMPTY.
        names:  dict mapping X and O to the names to display.
        pause:  seconds to sleep afterwards.
    """
    name = "the Cat" if winner == EMPTY else names[winner]
    print(f"\nAnd the winner is... {name}!!!\n")
    time.sleep(pause)


def print_stats(rows, games, elapsed=None, cpu=None):
    """Print how many games each side won, with percentages.

    Args:
        rows:    list of ``(label, win_count)`` pairs, one per side.
        games:   total games played (must be >= 1).
        elapsed: optional wall-clock seconds for the whole run.
        cpu:     optional processor seconds for the whole run.
    """
    played = f"{games:,} game was" if games == 1 else f"{games:,} games were"
    if elapsed is not None:
        print(f"{played} played in {elapsed:.2f} seconds.")
        print(f"Processor time utilized: {cpu:.4f} seconds.")
    else:
        print(f"{played} played.")
    for label, count in rows:
        label = label[0].upper() + label[1:]
        times = "time" if count == 1 else "times"
        print(f"{label} won {count:,} {times}.  Win rate {count / games:.2%}.")


def describe_history(brain, skipped, path):
    """Print a one-line summary of what was loaded from the history file."""
    if brain.games == 0:
        print(f"\nNo game history yet ({path}); the computer starts out knowing nothing.")
    else:
        print(f"\nLearned from {brain.games:,} past games in {path}.")
    if skipped:
        print(f"(Skipped {skipped:,} unreadable lines in the history file.)")


#
# Prompts
#
def prompt_choice(prompt, choices):
    """Ask until the answer (case-insensitive) is one of `choices`.

    Returns the answer upper-cased.
    """
    while True:
        answer = input(prompt).strip().upper()
        if answer in choices:
            return answer


def prompt_positive_int(prompt):
    """Ask until the answer is a whole number of 1 or more; return it."""
    while True:
        try:
            value = int(input(prompt))
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value >= 1:
            return value
        print("Please enter 1 or more.")


#
# Running a session
#
def benchmark(brain, games=BENCHMARK_GAMES):
    """Measure the brain against a random opponent, playing each side.

    The brain plays its best known move every time (no exploration) and
    learns nothing from these games.

    Returns:
        dict mapping X and O to a Counter with keys "won", "lost", "tied",
        counted from the brain's side, over `games` games as that mark.
    """
    learner = make_learning_player(brain)
    results = {}
    for mark in (X, O):
        players = {mark: learner, other(mark): random_player}
        counts = Counter()
        for _ in range(games):
            winner, _ = play_game(players)
            if winner == EMPTY:
                counts["tied"] += 1
            else:
                counts["won" if winner == mark else "lost"] += 1
        results[mark] = counts
    return results


def print_benchmarks(before, after, games=BENCHMARK_GAMES):
    """Print two benchmark() results side by side."""
    print(f"The computer vs a random opponent ({games:,} games as each side):")
    print(f"{'':16}{'Before':>9}{'After':>9}")
    for mark in (X, O):
        for outcome in ("won", "lost", "tied"):
            label = f"As {SYMBOLS[mark]}, {outcome}"
            print(f"  {label:<14}{before[mark][outcome] / games:>9.1%}"
                  f"{after[mark][outcome] / games:>9.1%}")


def run_display_games(games, pause, history_path):
    """Play `games` computer-vs-computer games, drawing every move.

    Both sides play the best moves in the history file (random if there is
    none). Nothing is learned or saved.
    """
    brain, skipped = load_brain(history_path)
    describe_history(brain, skipped, history_path)
    names = {X: "X", O: "O"}
    player = make_learning_player(brain)
    players = {X: player, O: player}

    def show(board):
        print(format_board(board), end="\n\n")
        time.sleep(pause)

    print("\n...playing...\n")
    results = Counter()
    for _ in range(games):
        winner, _ = play_game(players, on_move=show)
        results[winner] += 1
        announce_result(winner, names, pause * 3)
    rows = [(names[X], results[X]), (names[O], results[O]), ("the Cat", results[EMPTY])]
    print_stats(rows, games)


def opening_score(counts, mark=X):
    """Return `mark`'s average result (win 1, tie 0.5, loss 0) for a Counter
    of game results, or None if it holds no games."""
    games = sum(counts.values())
    if games == 0:
        return None
    return (counts[mark] + 0.5 * counts[EMPTY]) / games


def print_best_replies(brain):
    """Print O's best answer to each of X's nine possible first moves.

    For every first move, each reply O has played is scored from O's point
    of view (win 1, tie 0.5, loss 0) over the games in the history. Replies
    seen in fewer than MIN_REPLY_GAMES games are ignored, since a handful of
    games says little. Ends with the best replies laid out on the board, by
    where X opened.
    """
    print(f"\nBest reply for O to each first move (replies seen in fewer than "
          f"{MIN_REPLY_GAMES} games are ignored).")
    print("Replies that are rotations or mirror images of each other, given X's")
    print("first move, are the same move and are counted together.\n")
    print(f"{'X opens':<9}{'O replies':>10}{'Games':>10}{'O wins':>9}{'Ties':>9}"
          f"{'X wins':>9}{'Score':>9}")
    best_reply = {}
    for first in range(9):
        stabilizer = [perm for perm in SYMMETRIES if perm[first] == first]
        seen = set()
        candidates = []
        for reply in range(9):
            if reply == first or reply in seen:
                continue
            group = sorted({perm[reply] for perm in stabilizer})
            seen.update(group)
            counts = Counter()
            for square in group:
                counts.update(brain.replies.get((first, square), Counter()))
            if sum(counts.values()) >= MIN_REPLY_GAMES:
                candidates.append((-opening_score(counts, O), group, counts))
        if not candidates:
            print(f"{first + 1:<9}{'not enough data':>19}")
            continue
        negative_score, group, counts = min(candidates)   # best score, lowest squares on ties
        games = sum(counts.values())
        best_reply[first] = ",".join(str(square + 1) for square in group)
        print(f"{first + 1:<9}{best_reply[first]:>10}{games:>10,}{counts[O] / games:>9.1%}"
              f"{counts[EMPTY] / games:>9.1%}{counts[X] / games:>9.1%}{-negative_score:>9.3f}")

    print("\nBest reply, laid out by where X opened:\n")
    for row in (0, 3, 6):
        print("  " + " | ".join(
            best_reply.get(s, "-").ljust(7) for s in range(row, row + 3)
        ).rstrip())


def run_best_opening(history_path):
    """Analyze the history for the best first move, and O's best replies.

    Tallies, for each first move, how those games ended, and shows every
    square best-first, the same scores laid out on the board, and a summary
    by kind of square (center / corners / edges, which are equivalent by
    symmetry, so the kind is a steadier answer than any one square). Then
    shows O's best reply to each first move (see print_best_replies).

    The history comes from computer play that includes random exploration, so
    this ranks openings and replies by how they have done in that kind of
    play, not against perfect opponents.
    """
    brain, skipped = load_brain(history_path)
    describe_history(brain, skipped, history_path)
    if brain.games == 0:
        print("Nothing to analyze yet. Run Training mode (T) first.")
        return

    scored = []
    for square in range(9):
        counts = brain.openings.get(square, Counter())
        scored.append((opening_score(counts), square, counts))
    # Best first; squares never tried go last.
    scored.sort(key=lambda row: (row[0] is None, -(row[0] or 0), row[1]))

    print("\nBest first move for X, from the history (score: win = 1, tie = 0.5, loss = 0)\n")
    print(f"{'Square':<8}{'Games':>10}{'X wins':>9}{'Ties':>9}{'O wins':>9}{'Score':>9}")
    for rank, (score, square, counts) in enumerate(scored):
        games = sum(counts.values())
        if games == 0:
            print(f"{square + 1:<8}{0:>10,}    never played")
            continue
        note = "  <- best" if rank == 0 else ""
        print(f"{square + 1:<8}{games:>10,}{counts[X] / games:>9.1%}"
              f"{counts[EMPTY] / games:>9.1%}{counts[O] / games:>9.1%}{score:>9.3f}{note}")

    by_square = {square: score for score, square, _ in scored}
    print("\nScores on the board:\n")
    for row in (0, 3, 6):
        print("  " + " | ".join(
            "  -  " if by_square[s] is None else f"{by_square[s]:.3f}" for s in range(row, row + 3)
        ))

    print("\nBy kind of square:")
    for kind, squares in SQUARE_KINDS:
        combined = Counter()
        for square in squares:
            combined.update(brain.openings.get(square, Counter()))
        score = opening_score(combined)
        detail = "never played" if score is None else f"{sum(combined.values()):>10,} games, score {score:.3f}"
        print(f"  {kind:<8}{detail}")

    print_best_replies(brain)


def count_all_games(player, mark):
    """Count every possible game `player` can get, against any opponent play.

    `player` (a function ``f(board, mark) -> square``, which must not be
    random) moves as `mark` and always makes its one chosen move. Its opponent
    tries every open square at every turn, so this visits every distinct game
    that can be played against it, exactly once. Nothing is sampled.

    Returns:
        Counter with keys "won", "lost", "tied" (from `player`'s side).
    """
    counts = Counter()

    def explore(board, to_move, move):
        squares = [player(board, to_move)] if to_move == mark else open_squares(board)
        for square in squares:
            board[square] = to_move
            if move >= 5 and find_winner(board) != EMPTY:
                counts["won" if to_move == mark else "lost"] += 1
            elif move == 9:
                counts["tied"] += 1
            else:
                explore(board, other(to_move), move + 1)
            board[square] = EMPTY

    explore(new_board(), X, 1)
    return counts


def run_competition(history_path):
    """Compare history vs no history with no randomness at all.

    Two contestants: "history" (a Brain loaded from the history file) and
    "no history" (an empty Brain). Both always play their single best move,
    with ties settled by lowest square number, and neither learns. Shows:

    1. Every possible game against each contestant, as X and as O: the
       contestant makes its one move each turn while the opponent tries every
       possible move, and the games are counted (won / lost / tied).
    2. The four head-to-head pairings, one fixed game each (repeating them
       would only repeat the same game), with the moves as square numbers 1-9.
    """
    brain, skipped = load_brain(history_path)
    describe_history(brain, skipped, history_path)
    contestants = (
        ("history", make_learning_player(brain, deterministic=True)),
        ("no history", make_learning_player(Brain(), deterministic=True)),
    )

    print("\nNo randomness anywhere. Each contestant always plays its one best move,")
    print("while the opponent tries EVERY possible move. That covers every game")
    print("the opponent could possibly play, so these counts are exact.\n")
    print(f"{'Contestant':<18}{'Games':>8}{'Won':>8}{'Lost':>8}{'Tied':>8}")
    for name, player in contestants:
        for mark in (X, O):
            counts = count_all_games(player, mark)
            games = sum(counts.values())
            print(f"{name + ', as ' + SYMBOLS[mark]:<18}{games:>8,}{counts['won']:>8,}"
                  f"{counts['lost']:>8,}{counts['tied']:>8,}")

    print("\nHead to head (one fixed game each; moves are squares 1-9):\n")
    print(f"{'X plays':<12}{'O plays':<12}{'Result':<8}Moves")
    for x_name, x_player in contestants:
        for o_name, o_player in contestants:
            winner, moves = play_game({X: x_player, O: o_player})
            result = "Tie" if winner == EMPTY else f"{SYMBOLS[winner]} wins"
            print(f"{x_name:<12}{o_name:<12}{result:<8}{' '.join(str(s + 1) for s in moves)}")


def run_training_games(games, history_path):
    """Have the computer play itself `games` times, learning from each game.

    Each game is added to the brain immediately and appended to the history
    file. Prints the run's totals, how the results shifted from stage to
    stage, and a before/after comparison against a random opponent.
    """
    brain, skipped = load_brain(history_path)
    describe_history(brain, skipped, history_path)
    print("Measuring the starting skill level...")
    before = benchmark(brain)

    player = make_learning_player(brain, explore=EXPLORE_RATE)
    players = {X: player, O: player}
    stages = min(TREND_STAGES, games)
    trend = [Counter() for _ in range(stages)]
    results = Counter()

    print("\n...learning...\n")
    start_wall, start_cpu = time.perf_counter(), time.process_time()
    with open(history_path, "a+b") as history:
        # A valid final record may have no newline (for example after editing).
        # Inspect the last byte so the next game always starts on its own line.
        history.seek(0, 2)
        if history.tell():
            history.seek(-1, 2)
            if history.read(1) != b"\n":
                history.write(b"\n")
        for game_number in range(games):
            winner, moves = play_game(players)
            brain.learn(moves, winner)
            history.write((format_game(moves, winner) + "\n").encode("ascii"))
            results[winner] += 1
            trend[game_number * stages // games][winner] += 1
    elapsed = time.perf_counter() - start_wall
    cpu = time.process_time() - start_cpu

    rows = [("X", results[X]), ("O", results[O]), ("the Cat", results[EMPTY])]
    print_stats(rows, games, elapsed, cpu)

    print(f"\nSelf-play results by stage ({EXPLORE_RATE:.0%} random exploration throughout):")
    first = 1
    for number, stage in enumerate(trend, start=1):
        size = sum(stage.values())
        span = f"games {first:,}-{first + size - 1:,}"
        print(f"  Stage {number} ({span}):".ljust(38)
              + f"X {stage[X] / size:6.1%}   O {stage[O] / size:6.1%}"
              + f"   tie {stage[EMPTY] / size:6.1%}")
        first += size

    print("\nMeasuring the new skill level...\n")
    print_benchmarks(before, benchmark(brain))
    print(f"\nThe history file now holds {brain.games:,} games.")


def run_player_games(games):
    """Play `games` games of human vs computer and print a scoreboard.

    Before each game the human is asked whether to go first (as X) or
    second (as O). The board is redrawn with numbered empty squares before
    each human move. The scoreboard is by side ("You" / "the Computer"),
    regardless of which mark each played in a given game.
    """
    results = Counter()   # keys: "You", "the Computer", EMPTY (tie)
    for game_number in range(1, games + 1):
        human_first = prompt_choice("\nDo you want to go first? [Y/N] ", ("Y", "N")) == "Y"
        human_mark = X if human_first else O
        names = {human_mark: "You", other(human_mark): "the Computer"}
        players = {human_mark: human_player, other(human_mark): smart_player}

        print(f"\n--- Game {game_number} of {games}: you are {SYMBOLS[human_mark]} ---\n")
        winner, _ = play_game(
            players, on_move=lambda board: print(format_board(board, numbered=True), end="\n\n")
        )
        results[names.get(winner, EMPTY)] += 1
        announce_result(winner, names)
    rows = [("You", results["You"]), ("the Computer", results["the Computer"]),
            ("the Cat", results[EMPTY])]
    print_stats(rows, games)


def parse_args(argv):
    """Parse command-line options; all are optional (missing ones are prompted)."""
    parser = argparse.ArgumentParser(description="Play or simulate tic-tac-toe.")
    parser.add_argument(
        "--mode", type=str.upper,
        choices=(MODE_DISPLAY, MODE_TRAIN, MODE_COMPETE, MODE_BEST, MODE_PLAYER),
        help="D = display computer vs computer, T = training (computer "
             "plays itself and learns), C = competition (history vs no "
             "history, no randomness), B = analyze the best opening (first "
             "move and replies) from the history, P = you vs the computer",
    )
    parser.add_argument(
        "--games", type=int,
        help="number of games to play (not used by Competition or Best modes)",
    )
    parser.add_argument(
        "--pause", type=float, default=1.0,
        help="seconds to pause between moves in Display mode (default: 1)",
    )
    parser.add_argument(
        "--history", type=Path, default=DEFAULT_HISTORY,
        help=f"game history file (default: {DEFAULT_HISTORY})",
    )
    parser.add_argument("--seed", type=int, help="random seed, for repeatable runs")
    args = parser.parse_args(argv)
    if args.games is not None and args.games < 1:
        parser.error("--games must be 1 or more")
    if not math.isfinite(args.pause) or args.pause < 0:
        parser.error("--pause must be a finite, non-negative number")
    return args


def main(argv=None):
    """Program entry point. Returns the process exit status."""
    args = parse_args(argv)
    if args.seed is not None:
        random.seed(args.seed)
    try:
        mode = args.mode or prompt_choice(
            "\nChoose a mode: [D]isplay computer-vs-computer, "
            "[T]raining (computer plays itself and learns), "
            "[C]ompetition (history vs no history, no randomness), "
            "[B]est opening (best first move and replies, from the history), "
            "or [P]layer vs computer [D/T/C/B/P]? ",
            (MODE_DISPLAY, MODE_TRAIN, MODE_COMPETE, MODE_BEST, MODE_PLAYER),
        )
        if mode == MODE_COMPETE:
            run_competition(args.history)
        elif mode == MODE_BEST:
            run_best_opening(args.history)
        else:
            games = args.games or prompt_positive_int(
                "How many consecutive games would you like to play? "
            )
            if mode == MODE_PLAYER:
                run_player_games(games)
            elif mode == MODE_TRAIN:
                run_training_games(games, args.history)
            else:
                run_display_games(games, args.pause, args.history)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        return 1
    except OSError as error:
        print(f"\nError: {error}")
        return 2
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
