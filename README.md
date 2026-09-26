# Python Practice and Programming Fun

## tictactoe.py

A tic-tac-toe program that can play itself, learn from the games it plays,
analyze what it has learned, and play against you.

Originally written many years ago, reproduced from scratch in June 2022, and
updated in September 2026 to learn from its games.

**Requirements:** Python 3 (developed on a current 3.x). No third-party packages.

```
$ ./tictactoe.py            # asks which mode you want
$ ./tictactoe.py --help     # all options
```

### Modes

| Mode | Name | What it does |
|------|------|--------------|
| `D` | Display | Computer vs computer. Draws the board after every move so you can watch. |
| `T` | Training | The computer plays itself, silently and fast, and learns from every game. |
| `C` | Competition | History vs no history, with no randomness, to show what the history is worth. |
| `B` | Best opening | Analyzes the history for the best first move and O's best reply to each. |
| `P` | Player | You against the computer. |

Pick a mode at the prompt, or skip the prompt with `--mode`:

```
$ ./tictactoe.py --mode T --games 100000
$ ./tictactoe.py --mode D --games 1 --pause 0.5
$ ./tictactoe.py --mode C
$ ./tictactoe.py --mode B
$ ./tictactoe.py --mode P --games 3
```

| Option | Meaning |
|--------|---------|
| `--mode {D,T,C,B,P}` | Which mode to run (case-insensitive). Prompted for if left out. |
| `--games N` | How many games to play. Prompted for if left out. Not used by `C` and `B`. |
| `--pause SECONDS` | Delay between moves in Display mode (default 1). |
| `--history FILE` | Game history file (default: `history.txt` next to the script). |
| `--seed N` | Random seed, for repeatable runs. |

### How the computer learns

Every game is one line in the history file: the squares played in order
(0-8, top-left to bottom-right), then the result (`X`, `O`, or `T` for a tie):

```
7,8,5,4,1,2,6,3,0,T
```

Every board position along the way can be rebuilt from that line, so nothing
else needs to be stored. Lines that aren't real finished games are skipped
when the file is loaded.

From the history the computer builds a "brain". Each move is scored from the
point of view of the player who made it: 1 for a win, 0.5 for a tie, 0 for a
loss. For every (board position, move) pair the brain keeps the average score.
To move, it plays the open square with the best average. Squares it has never
tried count as 0.5, so it prefers untried moves to moves known to lose, but not
to moves known to win.

**Training is mostly history, plus some randomness.** 90% of the time the
computer plays its best known move. The other 10% it plays a random square, so
it keeps discovering moves it hasn't tried. Ties between equally good moves are
broken at random. Each game is added to the brain and appended to the history
file straight away, so it keeps getting better run after run.

### Training mode (`T`)

```
$ ./tictactoe.py --mode T --games 20000

No game history yet (history.txt); the computer starts out knowing nothing.
Measuring the starting skill level...

...learning...

20,000 games were played in 0.48 seconds.
Processor time utilized: 0.4836 seconds.
X won 5,326 times.  Win rate 26.63%.
O won 1,461 times.  Win rate 7.31%.
The Cat won 13,213 times.  Win rate 66.06%.

Self-play results by stage (10% random exploration throughout):
  Stage 1 (games 1-4,000):            X  39.7%   O  13.2%   tie  47.0%
  Stage 2 (games 4,001-8,000):        X  24.1%   O   7.2%   tie  68.7%
  Stage 3 (games 8,001-12,000):       X  24.0%   O   5.3%   tie  70.7%
  Stage 4 (games 12,001-16,000):      X  23.9%   O   5.8%   tie  70.3%
  Stage 5 (games 16,001-20,000):      X  21.5%   O   5.0%   tie  73.5%

Measuring the new skill level...

The computer vs a random opponent (2,000 games as each side):
                   Before    After
  As X, won         59.7%    98.9%
  As X, lost        28.2%     0.0%
  As X, tied        12.1%     1.1%
  As O, won         30.0%    80.5%
  As O, lost        57.8%    11.8%
  As O, tied        12.2%     7.8%

The history file now holds 20,000 games.
```

As the computer improves, self-play ties go up (two good players tie), and it
does much better against a random opponent. Run it again and it continues from
where it left off. After a few hundred thousand games it never loses as X and
loses only 1-2% as O against a random opponent. To start over, delete the
history file.

### Display mode (`D`)

Both sides play the best moves in the history (random play if there is none).
Nothing is learned or saved.

```
$ ./tictactoe.py --mode D --games 1

-|-|-
-|-|-
-|-|-

-|-|-
-|X|-
-|-|-

-|-|-
-|X|-
O|-|-

...
```

### Competition mode (`C`)

Compares a computer that uses the history with one that doesn't, with **no
randomness anywhere**: each contestant always plays its one best move (the
lowest square number breaks ties), and nothing is learned or saved. "No
history" is an empty brain, which just takes the lowest open square every time.

Because nothing is random, playing the same matchup twice would give the same
game. So instead of running many games, it counts **every possible game**: the
contestant plays its one move each turn while the opponent tries every possible
move, so the counts are exact.

```
Contestant           Games     Won    Lost    Tied
history, as X           98      94       0       4
history, as O          565     486       0      79
no history, as X       157      83      58      16
no history, as O       665     200     429      36

Head to head (one fixed game each; moves are squares 1-9):

X plays     O plays     Result  Moves
history     history     Tie     5 3 6 4 1 9 8 2 7
history     no history  X wins  5 1 2 3 8
no history  history     O wins  1 5 2 3 4 7
no history  no history  X wins  1 2 3 4 5 6 7
```

(Results from a 3,000,000-game history.) With history, the computer lost none
of its possible games. Without it, it lost 58 of 157 as X and 429 of 665 as O.

### Best opening (`B`)

Reads the history and, for each of the nine first-move squares, shows how many
games started there, how they ended, and a score (win = 1, tie = 0.5, loss = 0).
Then it shows O's best reply to each first move, with rotations and mirror
images counted together.

```
Square       Games   X wins     Ties   O wins    Score
5        2,727,181    21.9%    75.4%     2.6%    0.596  <- best
1           33,173    19.3%    69.7%    11.0%    0.542
...
By kind of square:
  Center   2,727,181 games, score 0.596
  Corners    139,273 games, score 0.539
  Edges      133,546 games, score 0.513
```

The center is the best first move, then corners, then edges. O's best reply to
any off-center opening is the center; against a center opening it is a corner.

Things to keep in mind when reading this:

- The history is computer self-play with random exploration. After training on
  itself the computer opens in the center in about 91% of games, so the other
  squares only have the games where exploration forced a different opening.
- With perfect play every opening ties. The scores show which openings give an
  opponent the most chances to go wrong.
- Small samples are noisy. Trust the totals by kind of square more than the
  ranking of individual squares, especially on a small history.

### Player mode (`P`)

You play the computer. Empty squares show their number, and you type the square
you want. Before each game you choose whether to go first (as X) or second
(as O), so you can play either side.

```
1|2|3
4|5|6
7|8|9

Your move (X), pick a square 1-9: 5
1|2|3
4|X|6
7|8|9

1|2|O
4|X|6
7|8|9
```

The computer in this mode takes a winning move if it has one, blocks yours if
you have one, and otherwise picks a random open square. It isn't unbeatable
(it doesn't set up or stop forks), but it never misses an immediate win or
loss. It doesn't use the history.

### The history file

- Default location: `history.txt` next to `tictactoe.py`. Change it with
  `--history`.
- It grows by about 19 bytes per game (3,000,000 games is about 57 MB), so you
  may want to keep it out of version control.
- Loading is the slow part: reading 3,000,000 games takes about 20 seconds in
  modes `T`, `D`, `C`, and `B`.
- To start learning from scratch, delete it, or point `--history` at a new file.
  `--history /tmp/trial.txt` is a handy way to experiment without touching the
  real one.

### How the code is organized

- **Game logic** (board, win detection, players, the brain) has no printing and
  no global state. `play_game()` returns the winner and the moves played.
- **Players are functions** with the signature `f(board, mark) -> square`, so
  `random_player`, `smart_player`, `human_player`, and the learning player all
  plug into the same game loop. A new kind of player is just a new function.
- **The board** is a flat list of 9 squares, read left to right, top to bottom,
  each `0` (empty), `1` (X), or `2` (O).
- Everything that prints or sleeps lives in the presentation helpers and the
  `run_*` functions.

### Ideas for later

- Save a compact summary of what the brain has learned, so startup is instant
  instead of replaying every game.
- Let Player mode's computer use the brain and learn from your games.
- Weight recent games more than old ones, so early random games count for less.
- Analyze X's best second move, following O's best reply.
