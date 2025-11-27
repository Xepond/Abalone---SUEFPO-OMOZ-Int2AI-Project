import sys
import time
import types
import random
from board import Board
from ai_engine import AbaloneAI

import math

# Runtime Patch: Dynamic Evaluate using self.weights
def dynamic_evaluate(self, board, player_color, move=None, move_maker_color=None):
    """
    Patched evaluation function that uses self.weights.
    User Weights: [Material, Push, Cohesion, Center, Danger]
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
    # [Material, Push, Cohesion, Center, Danger]
    w_mat = self.weights[0]
    w_agg = self.weights[1] # Push
    w_coh = self.weights[2]
    w_cen = self.weights[3]
    w_danger = self.weights[4]
    
    total_material = material_diff * w_mat
    total_aggression = aggression_score * w_agg
    total_cohesion = cohesion_score * w_coh
    total_center = center_score * w_cen
    total_danger = danger_penalty * w_danger
    
    score = total_material + total_aggression + total_cohesion + total_center + total_danger
    
    # Random Jitter to break ties/loops
    score += random.uniform(-500, 500)
    
    breakdown = {
        'Material': total_material,
        'Aggression': total_aggression,
        'Cohesion': total_cohesion,
        'Center': total_center,
        'Danger': total_danger,
        'Total': score
    }
    
    return score, breakdown

def patched_minimax_pure(self, board, depth, maximizing_player, start_time=None, last_move=None, progress_callback=None):
    """
    Patched Pure Minimax that strictly enforces time limit.
    """
    self.metrics['nodes_explored'] += 1
    
    if start_time and (self.metrics['nodes_explored'] % 100 == 0):
            elapsed = time.time() - start_time
            self.metrics['time_elapsed'] = elapsed
            
            if progress_callback:
                progress_callback()
                
            if elapsed > self.time_limit:
                # ABORT: Return heuristic immediately
                maker_color = self._get_opponent_color(self.my_color) if maximizing_player else self.my_color
                return self.evaluate(board, self.my_color, last_move, maker_color)[0]

    if depth == 0 or self._is_game_over(board):
        maker_color = self._get_opponent_color(self.my_color) if maximizing_player else self.my_color
        return self.evaluate(board, self.my_color, last_move, maker_color)[0]
        
    current_color = self.my_color if maximizing_player else self._get_opponent_color(self.my_color)
    moves = self.get_all_legal_moves(board, current_color)
    
    if not moves:
            maker_color = self._get_opponent_color(self.my_color) if maximizing_player else self.my_color
            return self.evaluate(board, self.my_color, last_move, maker_color)[0]
            
    if maximizing_player:
        max_eval = -math.inf
        for move in moves:
            sim_board = self._clone_board(board)
            sim_board.apply_move(move)
            eval_val = self.minimax_pure(sim_board, depth - 1, False, start_time, last_move=move, progress_callback=progress_callback)
            max_eval = max(max_eval, eval_val)
        return max_eval
    else:
        min_eval = math.inf
        for move in moves:
            sim_board = self._clone_board(board)
            sim_board.apply_move(move)
            eval_val = self.minimax_pure(sim_board, depth - 1, True, start_time, last_move=move, progress_callback=progress_callback)
            min_eval = min(min_eval, eval_val)
        return min_eval

class Arena:
    def __init__(self, match_count=4):
        self.match_count = match_count
        self.results = {
            "IDM_Wins": 0,
            "Champion_Wins": 0,
            "Draws": 0
        }

    def get_board_state(self, board):
        return tuple(sorted([(k, v.color) for k, v in board.grid.items()]))

    def run_match(self, match_id, p1_algo, p2_algo):
        """
        Run a single match.
        p1_algo: Algorithm for Black
        p2_algo: Algorithm for White
        """
        print(f"\n--- Match {match_id}: Black ({p1_algo}) vs White ({p2_algo}) ---")
        
        board = Board()
        board.init_board()
        
        # Initialize AIs
        # Champion (Minimax+ABP) gets 5.0s, ID Minimax gets 2.0s (Weaker CPU budget)
        t1 = 5.0 if p1_algo == "Minimax+ABP" else 2.0
        t2 = 5.0 if p2_algo == "Minimax+ABP" else 2.0
        
        ai_black = AbaloneAI()
        ai_black.set_config(p1_algo, 1, t1, 'B')
        
        ai_white = AbaloneAI()
        ai_white.set_config(p2_algo, 1, t2, 'W')
        
        # Default Weights: [Material, Push, Cohesion, Center, Danger]
        # Increased Push to 2000 to force contact
        default_weights = [10000, 2000, 10, 3, -250]
        
        # Inject Weights
        ai_black.weights = list(default_weights)
        ai_white.weights = list(default_weights)
        
        # Asymmetry: Boost Aggression for Champion
        if p1_algo == "Minimax+ABP":
            ai_black.weights[1] *= 1.2 # Boost Push
        if p2_algo == "Minimax+ABP":
            ai_white.weights[1] *= 1.2 # Boost Push
        
        # Bind Dynamic Evaluate (Patching 'evaluate' as it is the method called by engine)
        ai_black.evaluate = types.MethodType(dynamic_evaluate, ai_black)
        ai_white.evaluate = types.MethodType(dynamic_evaluate, ai_white)
        
        # Bind Patched Minimax Pure (for ID Minimax timeout fix)
        ai_black.minimax_pure = types.MethodType(patched_minimax_pure, ai_black)
        ai_white.minimax_pure = types.MethodType(patched_minimax_pure, ai_white)
        
        current_turn = 'B'
        move_count = 0
        history = {} 
        rage_mode = False
        
        while True:
            move_count += 1
            
            # 1. Repetition Check
            state = self.get_board_state(board)
            count = history.get(state, 0)
            if count >= 3:
                print(f"Match {match_id} Result: Draw (3-fold Repetition)")
                return 'D'
            history[state] = count + 1
            
            # 2. Rage Mode
            if move_count == 100 and board.black_score == 0 and board.white_score == 0 and not rage_mode:
                print("!!! RAGE MODE ACTIVATED !!!")
                # Multiply Material (0) and Push (1) by 100
                ai_black.weights[0] *= 100
                ai_black.weights[1] *= 100
                ai_white.weights[0] *= 100
                ai_white.weights[1] *= 100
                rage_mode = True
                
            # 3. Move Limit
            if move_count > 200:
                print("Move limit (200) reached.")
                if board.white_score > board.black_score:
                    return 'W'
                elif board.black_score > board.white_score:
                    return 'B'
                else:
                    return 'D'
            
            # 4. Get Move
            current_ai = ai_black if current_turn == 'B' else ai_white
            algo_name = p1_algo if current_turn == 'B' else p2_algo
            
            # print(f"DEBUG: Requesting move for {current_turn} ({algo_name})...")
            move = current_ai.get_best_move(board)
            # print(f"DEBUG: Move received: {move}")
            
            if not move:
                print(f"{current_turn} has no moves.")
                return 'W' if current_turn == 'B' else 'B'
                
            # 5. Log
            dq, dr = move['dir']
            marbles = str(move['marbles'][0]) if move['marbles'] else "[]"
            
            # Concise Log - Commented out to reduce noise
            # print(f"Move {move_count}: {algo_name} -> {move['type']} {marbles} (Score: {board.black_score}-{board.white_score})")
            
            # Milestone Logging
            if move_count % 20 == 0:
                 print(f"Move {move_count}... Score: B={board.black_score}, W={board.white_score}")
            
            # 6. Apply
            winner = board.apply_move(move)
            
            ai_black.update_history(board)
            ai_white.update_history(board)
            
            if winner:
                print(f"Match {match_id} Result: {winner} Wins! ({board.black_score}-{board.white_score})")
                return 'B' if winner == "Black" else 'W'
                
            current_turn = 'W' if current_turn == 'B' else 'B'

    def run_series(self):
        print(f"Starting Series: ID Minimax vs Champion ({self.match_count} games)")
        
        # ID Minimax vs Minimax+ABP
        algo1 = "ID Minimax"
        algo2 = "Minimax+ABP"
        
        for i in range(1, self.match_count + 1):
            # Swap sides
            if i <= self.match_count // 2:
                p1 = algo1 # Black
                p2 = algo2 # White
                p1_is_idm = True
            else:
                p1 = algo2 # Black
                p2 = algo1 # White
                p1_is_idm = False
                
            result = self.run_match(i, p1, p2)
            
            if result == 'D':
                self.results["Draws"] += 1
            elif result == 'B':
                if p1_is_idm: self.results["IDM_Wins"] += 1
                else: self.results["Champion_Wins"] += 1
            elif result == 'W':
                if not p1_is_idm: self.results["IDM_Wins"] += 1
                else: self.results["Champion_Wins"] += 1
                
        self.print_summary()

    def print_summary(self):
        print("\n=== Final Results ===")
        print(f"Champion (Minimax+AB) Wins: {self.results['Champion_Wins']}")
        print(f"ID Minimax (Pure) Wins: {self.results['IDM_Wins']}")
        print(f"Draws: {self.results['Draws']}")
        print("=====================")

if __name__ == "__main__":
    arena = Arena(match_count=4)
    arena.run_series()
