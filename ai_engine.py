import time
import random
import math

class AbaloneAI:
    def __init__(self):
        self.metrics = {
            'nodes_explored': 0,
            'execution_time': 0,
            'last_move_breakdown': {}
        }
        # Weights for evaluation: [Material, Center Control, Cohesion, Mobility]
        # Currently simple material weight
        self.weights = [1000, 10, 5, 1] 
        
        self.algorithm_type = "Greedy" # Default
        self.max_depth = 1
        self.time_limit = 3.0 # Seconds
        self.my_color = 'W' # Default
        
        self.position_history = [] # For repetition detection
        
        # Precompute Center Scores
        self.center_scores = {}
        self._precompute_center_scores()

    def _precompute_center_scores(self):
        """
        Precompute distance-based scores for all board positions.
        """
        for q in range(-4, 5):
            for r in range(-4, 5):
                if max(abs(q), abs(r), abs(-q-r)) <= 4:
                    dist = (abs(q) + abs(r) + abs(-q-r)) / 2
                    # Score: 5 - dist (Center=5, Edge=1)
                    self.center_scores[(q, r)] = 5 - dist

    def update_history(self, board):
        """
        Add current board state to history. Keep last 6.
        """
        state_hash = self._get_board_hash(board)
        self.position_history.append(state_hash)
        if len(self.position_history) > 6:
            self.position_history.pop(0)

    def _get_board_hash(self, board):
        """
        Generate a stable hash for the board grid.
        """
        return tuple(sorted([(k, v.color) for k, v in board.grid.items()]))

    def set_config(self, algorithm_type, max_depth, time_limit, my_color):
        self.algorithm_type = algorithm_type
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.my_color = my_color
        
    def get_best_move(self, board, progress_callback=None):
        """
        Main entry point. Returns the best move_data dictionary.
        """
        self.metrics = {
            'nodes_explored': 0,
            'execution_time': 0,
            'last_move_breakdown': {}
        }
        start_time = time.time()
        
        best_move = None
        
        if self.algorithm_type == "Greedy":
            best_move = self._greedy_logic(board)
        else:
            # Fallback or Not Implemented
            return None
            
        self.metrics['execution_time'] = time.time() - start_time
        return best_move

    def _greedy_logic(self, board):
        """
        Depth 1 search. Returns best move.
        """
        moves = self.get_all_legal_moves(board, self.my_color)
        if not moves:
            return None
            
        best_score = -math.inf
        best_move = None
        best_breakdown = {}
        
        for move in moves:
            sim_board = self._clone_board(board)
            sim_board.apply_move(move)
            # Pass move to evaluate for Aggression score
            score, breakdown = self.evaluate(sim_board, self.my_color, move)
            
            # Repetition Check
            sim_hash = self._get_board_hash(sim_board)
            if sim_hash in self.position_history:
                score -= 5000 # Massive penalty
                breakdown['Total'] = score # Update breakdown to reflect penalty
                breakdown['Repetition'] = -5000
            
            if score > best_score:
                best_score = score
                best_move = move
                best_breakdown = breakdown
        
        self.metrics['last_move_breakdown'] = best_breakdown
        return best_move



    def evaluate(self, board, player_color, move=None):
        """
        Heuristic evaluation. Returns (score, breakdown_dict).
        Optimized for speed.
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
                # Unroll loop slightly or just iterate
                q, r = pos
                neighbors = 0
                for dq, dr in directions:
                    if (q + dq, r + dr) in grid and grid[(q + dq, r + dr)].color == player_color:
                        neighbors += 1
                cohesion_score += neighbors
                
                # Danger (Edge penalty)
                # If score is 1 (dist 4), it's on edge
                if self.center_scores.get(pos, 0) == 1:
                    # Check if supported (has neighbors)
                    if neighbors == 0:
                        danger_penalty += 2 # Isolated on edge is bad
                    else:
                        danger_penalty += 0.5 # Supported on edge is okay-ish
            else:
                op_pieces += 1
        
        material_diff = my_pieces - op_pieces
        
        # Aggression (Pushing)
        if move and move.get('push_opponent'):
            # Bonus for pushing
            aggression_score = len(move['push_opponent']) * 2
            
            # Extra bonus if pushing towards edge?
            # Complex to calc, skip for now to keep speed
        
        # Weights (Tuned)
        w_mat = 10000   # Material is King (increased to avoid trading mistake)
        w_agg = 500     # Aggression (Pushing)
        w_coh = 10      # Cohesion (Group safety)
        w_cen = 20      # Center Control
        w_danger = -100 # Danger Penalty
        
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

    def get_ordered_moves(self, board, color):
        """
        Get moves sorted by promise (captures/pushes first).
        """
        moves = self.get_all_legal_moves(board, color)
        
        def move_priority(move):
            # Higher priority for pushes/captures
            if move['push_opponent']:
                return 10 + len(move['push_opponent'])
            return 0
            
        moves.sort(key=move_priority, reverse=True)
        return moves

    def get_all_legal_moves(self, board, color):
        """
        Generate all legal moves for the given color.
        """
        moves = []
        seen_moves = set() # To avoid duplicates
        
        # 1. Find all pieces of color
        pieces = [pos for pos, p in board.grid.items() if p.color == color]
        
        # Helper to add move if valid and new
        def try_add_move(selected, target_q, target_r):
            # We use board.validate_move logic
            # But validate_move expects 'selected' to be a list of tuples
            # and 'target' to be the clicked cell.
            
            # This is slightly inefficient because validate_move re-checks adjacency
            # But it ensures 100% consistency with game rules.
            
            move_data, _ = board.validate_move(selected, target_q, target_r)
            if move_data:
                # Create a hashable signature
                # (tuple(sorted(marbles)), dir)
                sig = (tuple(sorted(move_data['marbles'])), move_data['dir'])
                if sig not in seen_moves:
                    seen_moves.add(sig)
                    moves.append(move_data)

        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

        # Single Moves
        for q, r in pieces:
            for dq, dr in directions:
                try_add_move([(q, r)], q + dq, r + dr)

        # Line Moves (2 and 3)
        # We need to find lines of pieces
        # Iterate pieces, look for neighbors in specific directions (half of directions to avoid double counting)
        half_directions = [(1, 0), (0, 1), (1, -1)] 
        
        for q, r in pieces:
            for dq, dr in half_directions:
                # Check for 2
                n1 = (q + dq, r + dr)
                if n1 in board.grid and board.grid[n1].color == color:
                    group2 = [(q, r), n1]
                    
                    # Try Inline (Head moves)
                    # Head can be (q,r) moving to (q-dq, r-dr)
                    try_add_move(group2, q - dq, r - dr)
                    # Head can be n1 moving to (n1[0]+dq, n1[1]+dr)
                    try_add_move(group2, n1[0] + dq, n1[1] + dr)
                    
                    # Try Broadside
                    for b_dq, b_dr in directions:
                        if (b_dq, b_dr) != (dq, dr) and (b_dq, b_dr) != (-dq, -dr):
                            # For broadside, target can be any neighbor of the group in that direction
                            # validate_move handles the rest
                            try_add_move(group2, q + b_dq, r + b_dr)

                    # Check for 3
                    n2 = (n1[0] + dq, n1[1] + dr)
                    if n2 in board.grid and board.grid[n2].color == color:
                        group3 = [(q, r), n1, n2]
                        
                        # Try Inline
                        try_add_move(group3, q - dq, r - dr)
                        try_add_move(group3, n2[0] + dq, n2[1] + dr)
                        
                        # Try Broadside
                        for b_dq, b_dr in directions:
                            if (b_dq, b_dr) != (dq, dr) and (b_dq, b_dr) != (-dq, -dr):
                                try_add_move(group3, q + b_dq, r + b_dr)

        return moves

    def _clone_board(self, board):
        """
        Create a deep copy of the board for simulation.
        """
        return board.clone()

    def _get_opponent_color(self, color):
        return 'B' if color == 'W' else 'W'
        
    def _is_game_over(self, board):
        return board.white_score >= 6 or board.black_score >= 6

    def _get_state_key(self, board, is_max):
        # Simple hash of grid keys and current player
        # board.grid keys are (q,r), values are Piece(color)
        # We need a string or tuple representation
        grid_tuple = tuple(sorted([(k, v.color) for k, v in board.grid.items()]))
        return (grid_tuple, is_max)
