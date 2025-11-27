import sys
import time
import types
from board import Board
from ai_engine import AbaloneAI

# Runtime Patch: Dynamic Evaluate using self.weights
def dynamic_evaluate(self, board, player_color, move=None, move_maker_color=None):
    """
    Patched evaluation function that uses self.weights.
    weights indices: [0: Material, 1: Center, 2: Cohesion, 3: Aggression, 4: Danger]
    """
    # 1. Material & Position
    my_pieces = 0
    op_pieces = 0
    
    center_score = 0
    cohesion_score = 0
    danger_penalty = 0
    aggression_score = 0
    
    # Directions for neighbors
    directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
    
    # Single pass through grid
    grid = board.grid
    
    for pos, piece in grid.items():
        if piece.color == player_color:
            my_pieces += 1
            
            # Center Control (Lookup)
            center_score += self.center_scores.get(pos, 0)
            
            # Cohesion (Neighbor count)
            q, r = pos
            neighbors = 0
            for dq, dr in directions:
                if (q + dq, r + dr) in grid and grid[(q + dq, r + dr)].color == player_color:
                    neighbors += 1
            cohesion_score += neighbors
            
            # Danger (Edge penalty)
            if self.center_scores.get(pos, 0) == 1:
                if neighbors == 0:
                    danger_penalty += 2
                else:
                    danger_penalty += 0.5
        else:
            op_pieces += 1
    
    material_diff = my_pieces - op_pieces
    
    # Aggression (Pushing)
    if move and move.get('push_opponent'):
        base_agg = len(move['push_opponent']) * 2
        if move_maker_color == player_color:
            aggression_score = base_agg
        elif move_maker_color:
            aggression_score = -base_agg
    
    # Use Dynamic Weights
    # [Material, Center, Cohesion, Aggression, Danger]
    w_mat = self.weights[0]
    w_cen = self.weights[1]
    w_coh = self.weights[2]
    w_agg = self.weights[3]
    w_danger = self.weights[4]
    
    total_material = material_diff * w_mat
    total_aggression = aggression_score * w_agg
    total_cohesion = cohesion_score * w_coh
    total_center = center_score * w_cen
    total_danger = danger_penalty * w_danger
    
    score = total_material + total_aggression + total_cohesion + total_center + total_danger
    
    breakdown = {
        'Material': total_material,
        'Aggression': total_aggression,
        'Cohesion': total_cohesion,
        'Center': total_center,
        'Danger': total_danger,
        'Total': score
    }
    
    return score, breakdown

class Arena:
    def __init__(self, ai1_type, ai2_type, match_count=4):
        self.ai1_type = ai1_type
        self.ai2_type = ai2_type
        self.match_count = match_count
        self.results = {
            "AI1_Wins": 0,
            "AI2_Wins": 0,
            "Draws": 0
        }

    def get_board_state(self, board):
        """
        Serialize the board state to a hashable tuple for repetition detection.
        Format: tuple of ((q, r), color) sorted by position.
        """
        return tuple(sorted([(k, v.color) for k, v in board.grid.items()]))

    def run_match(self, match_id, p1_type, p2_type):
        """
        Run a single match between p1 (Black) and p2 (White).
        Returns: 'B' (Black Wins), 'W' (White Wins), or 'D' (Draw).
        """
        print(f"\n--- Match {match_id}: Black ({p1_type}) vs White ({p2_type}) ---")
        
        board = Board()
        board.init_board()
        
        # Initialize AIs
        ai_black = AbaloneAI()
        ai_black.set_config(p1_type, 1, 3.0, 'B')
        
        ai_white = AbaloneAI()
        ai_white.set_config(p2_type, 1, 3.0, 'W')
        
        # Runtime Patching for Rage Mode support
        # Set weights: [Material, Center, Cohesion, Aggression, Danger]
        # Default values from ai_engine.py
        default_weights = [10000, 20, 10, 500, -100]
        
        ai_black.weights = list(default_weights)
        ai_white.weights = list(default_weights)
        
        # Bind new evaluate method
        ai_black.evaluate = types.MethodType(dynamic_evaluate, ai_black)
        ai_white.evaluate = types.MethodType(dynamic_evaluate, ai_white)
        
        current_turn = 'B'
        move_count = 0
        history = {} # Map state_hash -> count
        
        rage_mode_triggered = False
        
        while True:
            move_count += 1
            
            # 1. Repetition Check
            state = self.get_board_state(board)
            count = history.get(state, 0)
            if count >= 3:
                print(f"Match {match_id} Result: Draw (3-fold Repetition) (Score: B={board.black_score}, W={board.white_score})")
                return 'D'
            history[state] = count + 1
            
            # 2. Rage Mode Check (Move 100, 0-0 score)
            if move_count == 100 and board.black_score == 0 and board.white_score == 0 and not rage_mode_triggered:
                print("!!! RAGE MODE ACTIVATED !!! Increasing Aggression & Material weights!")
                # Multiply Material (0) and Aggression (3) by 100
                ai_black.weights[0] *= 100
                ai_black.weights[3] *= 100
                ai_white.weights[0] *= 100
                ai_white.weights[3] *= 100
                rage_mode_triggered = True
            
            # 3. Move Limit & Sudden Death
            if move_count > 200:
                print(f"Move limit (200) reached. Sudden Death Tie-Breaker.")
                if board.white_score > board.black_score:
                    print(f"Match {match_id} Result: White Wins (Score: B={board.black_score}, W={board.white_score})")
                    return 'W'
                elif board.black_score > board.white_score:
                    print(f"Match {match_id} Result: Black Wins (Score: B={board.black_score}, W={board.white_score})")
                    return 'B'
                else:
                    print(f"Match {match_id} Result: Draw (Equal Score) (Score: B={board.black_score}, W={board.white_score})")
                    return 'D'
            
            # 4. Get Move
            current_ai = ai_black if current_turn == 'B' else ai_white
            algo_name = p1_type if current_turn == 'B' else p2_type
            
            move = current_ai.get_best_move(board)
            
            if not move:
                print(f"Match {match_id} Result: {current_turn} has no moves. Opponent Wins.")
                return 'W' if current_turn == 'B' else 'B'
                
            # 5. Log Move
            dq, dr = move['dir']
            marbles_str = str(move['marbles'][0]) if move['marbles'] else "[]"
            # print(f"Move {move_count}: {'Black' if current_turn == 'B' else 'White'} ({algo_name}) -> {move['type']} {marbles_str}")
            
            # 6. Apply Move
            winner = board.apply_move(move)
            
            ai_black.update_history(board)
            ai_white.update_history(board)
            
            if winner:
                print(f"Match {match_id} Result: {winner} Wins! (Score: B={board.black_score}, W={board.white_score})")
                return 'B' if winner == "Black" else 'W'
                
            # 7. Switch Turn
            current_turn = 'W' if current_turn == 'B' else 'B'

    def run_series(self):
        print(f"Starting Series: {self.ai1_type} vs {self.ai2_type} ({self.match_count} games)")
        
        for i in range(1, self.match_count + 1):
            # Swap sides halfway
            if i <= self.match_count // 2:
                p1 = self.ai1_type # Black
                p2 = self.ai2_type # White
                p1_is_ai1 = True
            else:
                p1 = self.ai2_type # Black
                p2 = self.ai1_type # White
                p1_is_ai1 = False
                
            result = self.run_match(i, p1, p2)
            
            if result == 'D':
                self.results["Draws"] += 1
            elif result == 'B':
                if p1_is_ai1: self.results["AI1_Wins"] += 1
                else: self.results["AI2_Wins"] += 1
            elif result == 'W':
                if not p1_is_ai1: self.results["AI1_Wins"] += 1
                else: self.results["AI2_Wins"] += 1
                
        self.print_summary()

    def print_summary(self):
        print("\n=== Final Results ===")
        print(f"{self.ai1_type} Wins: {self.results['AI1_Wins']}")
        print(f"{self.ai2_type} Wins: {self.results['AI2_Wins']}")
        print(f"Draws (Loops/Limit): {self.results['Draws']}")
        print("=====================")

if __name__ == "__main__":
    # Configuration
    AI1 = "Greedy"
    AI2 = "ID Minimax"
    MATCHES = 4
    
    arena = Arena(AI1, AI2, MATCHES)
    arena.run_series()
