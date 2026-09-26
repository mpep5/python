"""Regression tests; run with python3 -m unittest -v."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tictactoe as game


class InputTests(unittest.TestCase):
    def test_invalid_moves_reprompt_instead_of_crashing(self):
        board = game.new_board()
        board[0] = game.X
        entries = ['²', '', 'abc', '9' * 5000, '0', '10', '1', '2']
        with patch('builtins.input', side_effect=entries), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(game.human_player(board, game.O), 1)
        self.assertEqual(board, [game.X] + [game.EMPTY] * 8)

    def test_player_yes_no_rejects_blank_and_combined_answers(self):
        # Exercise the session caller too: it must pass discrete choices.
        for answer, expected_mark in [('y', game.X), ('n', game.O)]:
            with self.subTest(answer=answer):
                with patch('builtins.input', side_effect=['', 'YN', answer]) as read, \
                     patch.object(game, 'play_game', return_value=(game.EMPTY, [])) as play, \
                     contextlib.redirect_stdout(io.StringIO()):
                    game.run_player_games(1)
                self.assertEqual(read.call_count, 3)
                self.assertIs(play.call_args.args[0][expected_mark], game.human_player)

    def test_pause_rejects_nonfinite_and_negative_values(self):
        for value in ['nan', 'inf', '-inf', '-0.1']:
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    game.parse_args(['--pause=' + value])
                self.assertEqual(result.exception.code, 2)
        for value in ['0', '0.5', '1']:
            self.assertEqual(game.parse_args(['--pause', value]).pause, float(value))


class HistoryTests(unittest.TestCase):
    def test_training_preserves_records_with_or_without_final_newline(self):
        record = b'0,3,1,4,2,X'
        cases = [None, b'', record, record + b'\n', record + b'\r\n', b'bad record']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.txt'
            for initial in cases:
                with self.subTest(initial=initial):
                    path.unlink(missing_ok=True)
                    if initial is not None:
                        path.write_bytes(initial)
                    # Benchmarks do not affect the persistence behavior under test.
                    with patch.object(game, 'benchmark', return_value={}), \
                         patch.object(game, 'print_benchmarks'), \
                         contextlib.redirect_stdout(io.StringIO()):
                        game.run_training_games(2, path)
                    brain, skipped = game.load_brain(path)
                    existing = int(initial is not None and initial.startswith(record))
                    self.assertEqual(brain.games, existing + 2)
                    self.assertEqual(skipped, int(initial == b'bad record'))
                    if existing:
                        self.assertEqual(path.read_bytes().splitlines()[0], record)


if __name__ == '__main__':
    unittest.main()
