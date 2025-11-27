from board import Board
from ai_engine import AbaloneAI
import time

def test_champion():
    print("Initializing Board...")
    board = Board()
    board.init_board()
    
    print("Initializing AI (Minimax+ABP)...")
    ai = AbaloneAI()
    ai.set_config("Minimax+ABP", 1, 2.0, 'B') # 2 seconds limit for test
    
    print("Getting Best Move...")
    start = time.time()
    move = ai.get_best_move(board)
    duration = time.time() - start
    
    print(f"Move found in {duration:.2f}s")
    print(f"Move: {move}")
    print(f"Metrics: {ai.metrics}")
    
    if move:
        print("SUCCESS: Move generated.")
    else:
        print("FAILURE: No move generated.")

if __name__ == "__main__":
    test_champion()
