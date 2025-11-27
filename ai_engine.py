import time
import random
import math

class AbaloneAI:
    def __init__(self):
        self.metrics = {
            'nodes_explored': 0,
            'execution_time': 0,
            'last_move_breakdown': {},
            'depth_history': [],
            'current_depth': 0,
            'time_elapsed': 0,
            'cutoffs': 0,
            'cache_hits': 0
        }
        # Weights for evaluation: [Material, Center Control, Cohesion, Mobility]
        # Currently simple material weight
        self.weights = [1000, 10, 5, 1] 
        
        self.algorithm_type = "Greedy" # Default
        self.max_depth = 1
        self.time_limit = 3.0 # Seconds
        self.my_color = 'W' # Default
        
        self.position_history = [] # For repetition detection
        
        # Transposition Table
        self.transposition_table = {}
        self.tt_hits = 0
        
        # Zobrist Hashing Initialization
        self.zobrist_table = {}
        self.turn_hash = random.getrandbits(64)
        self._init_zobrist()
        
        # Precompute Center Scores
        self.center_scores = {}
        self._precompute_center_scores()

    def _init_zobrist(self):
        """
        Initialize Zobrist table with random 64-bit integers.
        """
        # Board range is roughly -4 to 4, but let's cover all possible keys
        # We'll use a dictionary for sparse storage or just generate on fly? 
        # Better to precompute for speed.
        pieces = ['B', 'W']
        for q in range(-9, 10): # Generous range
            for r in range(-9, 10):
                for p in pieces:
                    self.zobrist_table[(q, r, p)] = random.getrandbits(64)

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
        
        # Set Algorithm-Specific Weights
        # [Material, Push, Cohesion, Center, Danger]
        if self.algorithm_type == "Greedy":
            # Aggressive Scavenger
            self.weights = [10000, 200, 10, 3, -250]
        elif self.algorithm_type in ["ID Minimax", "IDS"]:
            # Balanced Strategist
            self.weights = [10000, 100, 20, 50, -50]
        elif self.algorithm_type == "Minimax+ABP":
            # The Champion (Same as IDS for now)
            self.weights = [10000, 100, 20, 50, -50]
        else:
            # Default fallback
            self.weights = [10000, 100, 10, 20, -100]
        
    def get_best_move(self, board, progress_callback=None):
        """
        Main entry point. Returns the best move_data dictionary.
        """
        self.metrics = {
            'nodes_explored': 0,
            'execution_time': 0,
            'last_move_breakdown': {},
            'depth_history': [],
            'current_depth': 0,
            'time_elapsed': 0,
            'cutoffs': 0,
            'cache_hits': 0
        }
        start_time = time.time()
        
        # Reset TT stats for this move (optional, or keep cumulative)
        self.metrics['cache_hits'] = 0
        self.metrics['cutoffs'] = 0
        
        best_move = None
        
        if self.algorithm_type == "Greedy":
            best_move = self._greedy_logic(board)
        elif self.algorithm_type in ["ID Minimax", "IDS"]:
            best_move = self._ids_logic(board, progress_callback)
        elif self.algorithm_type == "Minimax+ABP":
            best_move = self.champion_search(board, progress_callback)
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
            score, breakdown = self.evaluate(sim_board, self.my_color, move, self.my_color)
            
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

    def _ids_logic(self, board, progress_callback=None):
        """
        Iterative Deepening Search.
        """
        final_best_move = None
        start_time = time.time()
        current_depth = 1
        
        while True:
            # Time Check
            elapsed = time.time() - start_time
            self.metrics['time_elapsed'] = elapsed
            if elapsed > self.time_limit:
                break
            
            # Update depth immediately so UI shows it
            self.metrics['current_depth'] = current_depth
            
            # Visual Slowdown
            time.sleep(0.1)
                
            # Root Search for this depth
            moves = self.get_all_legal_moves(board, self.my_color)
            random.shuffle(moves) # Add randomness
            
            best_score = -math.inf
            best_move_this_depth = None
            
            # If no moves, break
            if not moves:
                break
                
            timeout = False
            for move in moves:
                # Check time inside the loop too for finer granularity
                if time.time() - start_time > self.time_limit:
                    timeout = True
                    break
                    
                sim_board = self._clone_board(board)
                sim_board.apply_move(move)
                
                # Call pure minimax
                score = self.minimax_pure(sim_board, current_depth - 1, False, start_time, last_move=move, progress_callback=progress_callback)
                
                if score > best_score:
                    best_score = score
                    best_move_this_depth = move
            
            if timeout:
                break
                
            # Completed depth successfully
            self.metrics['current_depth'] = current_depth
            self.metrics['score'] = best_score
            # Store history: (depth, score) - simplified for UI
            self.metrics['depth_history'].append((current_depth, best_score))
            
            final_best_move = best_move_this_depth
            
            # Detailed Metrics Calculation for ID Minimax
            if final_best_move:
                sim_board = self._clone_board(board)
                sim_board.apply_move(final_best_move)
                # Get breakdown
                _, breakdown = self.evaluate(sim_board, self.my_color, final_best_move, self.my_color)
                self.metrics['last_move_breakdown'] = breakdown
            
            current_depth += 1
            
        return final_best_move

    def champion_search(self, board, progress_callback=None):
        """
        Champion Algorithm: Time-Managed Minimax + Alpha-Beta Pruning.
        """
        final_best_move = None
        start_time = time.time()
        current_depth = 1
        self.time_limit = 5.0 # Increased for Champion
        
        while True:
            # Time Check
            elapsed = time.time() - start_time
            self.metrics['time_elapsed'] = elapsed
            if elapsed > self.time_limit:
                break
                
            self.metrics['current_depth'] = current_depth
            time.sleep(0.1) # Visual visualization
            
            # Root Search
            moves = self.get_ordered_moves(board, self.my_color)
            
            best_score = -math.inf
            best_move_this_depth = None
            alpha = -math.inf
            beta = math.inf
            
            if not moves:
                break
                
            timeout = False
            for move in moves:
                if time.time() - start_time > self.time_limit:
                    timeout = True
                    break
                    
                sim_board = self._clone_board(board)
                sim_board.apply_move(move)
                
                score = self.minimax_ab(sim_board, current_depth - 1, alpha, beta, False, start_time, last_move=move, progress_callback=progress_callback)
                
                if score > best_score:
                    best_score = score
                    best_move_this_depth = move
                
                alpha = max(alpha, best_score)
                
            if timeout:
                break
                
            self.metrics['current_depth'] = current_depth
            self.metrics['score'] = best_score
            self.metrics['depth_history'].append((current_depth, best_score))
            
            final_best_move = best_move_this_depth
            
            # Metrics update
            if final_best_move:
                sim_board = self._clone_board(board)
                sim_board.apply_move(final_best_move)
                _, breakdown = self.evaluate(sim_board, self.my_color, final_best_move, self.my_color)
                self.metrics['last_move_breakdown'] = breakdown
            
            current_depth += 1
            
        return final_best_move

    def get_noisy_moves(self, board, color):
        """
        Get only tactical moves (Sumito/Push) for Quiescence Search.
        """
        moves = []
        all_moves = self.get_all_legal_moves(board, color)
        for move in all_moves:
            if move['push_opponent']:
                moves.append(move)
        return moves

    def quiescence_search(self, board, alpha, beta, maximizing_player, q_depth=2):
        """
        Quiescence Search to mitigate Horizon Effect.
        Searches only noisy moves (pushes) to reach a stable state.
        """
        self.metrics['nodes_explored'] += 1
        
        # 1. Stand-Pat (Static Evaluation)
        maker_color = self._get_opponent_color(self.my_color) if maximizing_player else self.my_color
        stand_pat = self.evaluate(board, self.my_color, None, maker_color)[0]
        
        if maximizing_player:
            if stand_pat >= beta:
                return beta
            if stand_pat > alpha:
                alpha = stand_pat
        else:
            if stand_pat <= alpha:
                return alpha
            if stand_pat < beta:
                beta = stand_pat
                
        # 2. Depth Limit
        if q_depth == 0:
            return stand_pat
            
        # 3. Search Noisy Moves
        current_color = self.my_color if maximizing_player else self._get_opponent_color(self.my_color)
        moves = self.get_noisy_moves(board, current_color)
        
        if not moves:
            return stand_pat
            
        # Move Ordering (Crucial for QS)
        def move_priority(move):
            return len(move['push_opponent'])
        moves.sort(key=move_priority, reverse=True)
        
        if maximizing_player:
            for move in moves:
                sim_board = self._clone_board(board)
                sim_board.apply_move(move)
                score = self.quiescence_search(sim_board, alpha, beta, False, q_depth - 1)
                
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
            return alpha
        else:
            for move in moves:
                sim_board = self._clone_board(board)
                sim_board.apply_move(move)
                score = self.quiescence_search(sim_board, alpha, beta, True, q_depth - 1)
                
                if score <= alpha:
                    return alpha
                if score < beta:
                    beta = score
            return beta

    def minimax_ab(self, board, depth, alpha, beta, maximizing_player, start_time, last_move=None, progress_callback=None):
        """
        Minimax with Alpha-Beta Pruning and Transposition Table.
        """
        self.metrics['nodes_explored'] += 1
        
        # TT Lookup
        state_key = self._get_state_key(board, maximizing_player)
        if state_key in self.transposition_table:
            entry = self.transposition_table[state_key]
            if entry['depth'] >= depth:
                if entry['flag'] == 'exact':
                    self.metrics['cache_hits'] += 1
                    return entry['score']
                elif entry['flag'] == 'lower' and entry['score'] > alpha:
                    alpha = entry['score']
                elif entry['flag'] == 'upper' and entry['score'] < beta:
                    beta = entry['score']
                if alpha >= beta:
                    self.metrics['cache_hits'] += 1
                    return entry['score']

        # Base Case
        if depth == 0 or self._is_game_over(board):
            # Use Quiescence Search at leaf nodes instead of raw eval
            return self.quiescence_search(board, alpha, beta, maximizing_player)
            
        current_color = self.my_color if maximizing_player else self._get_opponent_color(self.my_color)
        moves = self.get_ordered_moves(board, current_color)
        
        if not moves:
             maker_color = self._get_opponent_color(self.my_color) if maximizing_player else self.my_color
             return self.evaluate(board, self.my_color, last_move, maker_color)[0]

        if maximizing_player:
            max_eval = -math.inf
            for move in moves:
                # Time Check (Optimized: check every 100 nodes)
                if self.metrics['nodes_explored'] % 100 == 0:
                    if time.time() - start_time > self.time_limit:
                        return max_eval # Return current best to unwind
                
                sim_board = self._clone_board(board)
                sim_board.apply_move(move)
                eval_val = self.minimax_ab(sim_board, depth - 1, alpha, beta, False, start_time, last_move=move, progress_callback=progress_callback)
                max_eval = max(max_eval, eval_val)
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    self.metrics['cutoffs'] += 1
                    break
            
            # TT Store
            flag = 'exact'
            if max_eval <= alpha: flag = 'upper'
            elif max_eval >= beta: flag = 'lower'
            self.transposition_table[state_key] = {'score': max_eval, 'depth': depth, 'flag': flag}
            return max_eval
        else:
            min_eval = math.inf
            for move in moves:
                if self.metrics['nodes_explored'] % 100 == 0:
                    if time.time() - start_time > self.time_limit:
                        return min_eval

                sim_board = self._clone_board(board)
                sim_board.apply_move(move)
                eval_val = self.minimax_ab(sim_board, depth - 1, alpha, beta, True, start_time, last_move=move, progress_callback=progress_callback)
                min_eval = min(min_eval, eval_val)
                beta = min(beta, eval_val)
                if beta <= alpha:
                    self.metrics['cutoffs'] += 1
                    break
            
            # TT Store
            flag = 'exact'
            if min_eval <= alpha: flag = 'upper'
            elif min_eval >= beta: flag = 'lower'
            self.transposition_table[state_key] = {'score': min_eval, 'depth': depth, 'flag': flag}
            return min_eval

    def minimax_pure(self, board, depth, maximizing_player, start_time=None, last_move=None, progress_callback=None):
        """
        Inefficient Recursive Engine (Pure Minimax).
        No Alpha-Beta, No Cache.
        """
        self.metrics['nodes_explored'] += 1
        
        # Check time occasionally to abort deep searches if needed
        # But strict pure minimax usually runs to completion or we handle timeout at root.
        # However, if we want to break out of a deep recursion on timeout:
        if start_time and (self.metrics['nodes_explored'] % 100 == 0):
             elapsed = time.time() - start_time
             self.metrics['time_elapsed'] = elapsed
             
             if progress_callback:
                 progress_callback()
                 
             if elapsed > self.time_limit:
                 # We can't easily raise exception without catching it everywhere or handling it.
                 # For simplicity, let's just return a heuristic value to finish quickly,
                 # but the root loop checks time.
                 pass

        if depth == 0 or self._is_game_over(board):
            # Determine who made the last move for evaluation
            # If maximizing_player is True (It's MY turn), then the LAST move was made by OPPONENT.
            # If maximizing_player is False (It's OPPONENT'S turn), then the LAST move was made by ME.
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

    def evaluate(self, board, player_color, move=None, move_maker_color=None):
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
            base_agg = len(move['push_opponent']) * 2
            
            # If I made the move, it's good. If opponent made it, it's bad (for me).
            if move_maker_color == player_color:
                aggression_score = base_agg
            elif move_maker_color:
                aggression_score = -base_agg
            
            # Extra bonus if pushing towards edge?
            # Complex to calc, skip for now to keep speed
        
        # Weights (Dynamic)
        # [Material, Push, Cohesion, Center, Danger]
        w_mat = self.weights[0]
        w_agg = self.weights[1]
        w_coh = self.weights[2]
        w_cen = self.weights[3]
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
        """
        Calculate Zobrist Hash for the board state.
        """
        h = 0
        for pos, piece in board.grid.items():
            # pos is (q, r), piece.color is 'B' or 'W'
            # XOR with the random value for this piece at this position
            # If key missing (out of bounds?), skip or 0. Should be in bounds.
            z_key = (pos[0], pos[1], piece.color)
            if z_key in self.zobrist_table:
                h ^= self.zobrist_table[z_key]
        
        # XOR for turn if maximizing player
        if is_max:
            h ^= self.turn_hash
            
        return h
