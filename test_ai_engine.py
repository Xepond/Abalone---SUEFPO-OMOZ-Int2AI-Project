import unittest
import time
from board import Board
from ai_engine import AbaloneAI

class TestAbaloneAI(unittest.TestCase):
    def setUp(self):
        self.board = Board()
        self.board.init_board()
        self.ai = AbaloneAI()
        self.ai.my_color = 'W' # Default AI color

    def test_move_generation_initial_state(self):
        print("\nTesting Move Generation (Initial State)...")
        moves = self.ai.get_all_legal_moves(self.board, 'W')
        print(f"Number of moves found for White: {len(moves)}")
        # In standard setup, White has many moves.
        # Just checking it's not empty.
        self.assertTrue(len(moves) > 0)
        
        # Check structure of a move
        move = moves[0]
        self.assertIn('type', move)
        self.assertIn('dir', move)
        self.assertIn('marbles', move)

    def test_greedy_search(self):
        print("\nTesting Greedy Search...")
        self.ai.set_config("Greedy", 1, 1.0, 'W')
        move = self.ai.get_best_move(self.board)
        print(f"Greedy Move: {move}")
        self.assertIsNotNone(move)

    def test_ids_search(self):
        print("\nTesting IDS Search...")
        self.ai.set_config("IDS", 1, 1.5, 'W') # 1.5s limit
        start = time.time()
        move = self.ai.get_best_move(self.board)
        elapsed = time.time() - start
        print(f"IDS Move: {move}")
        print(f"Metrics: {self.ai.metrics}")
        
        self.assertIsNotNone(move)
        self.assertGreater(self.ai.metrics['current_depth'], 0)
        self.assertGreater(self.ai.metrics['nodes_explored'], 0)
        # Should run for at least the time limit roughly
        self.assertGreaterEqual(elapsed, 1.5)

if __name__ == '__main__':
    unittest.main()
