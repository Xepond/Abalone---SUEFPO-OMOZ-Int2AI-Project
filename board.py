class Piece:
    def __init__(self, color):
        self.color = color

    def __repr__(self):
        return f"Piece({self.color})"

DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

class Board:
    def __init__(self):
        self.grid = {} # {(q, r): Piece}
        self.selected = [] # List of (q, r) tuples
        self.black_score = 0
        self.white_score = 0

    def add_piece(self, q, r, color):
        self.grid[(q, r)] = Piece(color)

    def get_neighbors(self, q, r):
        neighbors = []
        for dq, dr in DIRECTIONS:
            neighbors.append((q + dq, r + dr))
        return neighbors

    def handle_click(self, q, r, current_turn_color):
        """
        Handle a click at (q, r). Returns True if a move was made, False otherwise.
        """
        piece = self.grid.get((q, r))
        
        # Case 1: Clicked on own piece -> Select/Deselect
        if piece and piece.color == current_turn_color:
            if (q, r) in self.selected:
                self.selected.remove((q, r))
            else:
                # Max 3 constraint
                if len(self.selected) >= 3:
                    self.selected = []
                self.selected.append((q, r))
            return False
            
        # Case 2: Clicked on empty or opponent -> Try Move
        elif self.selected:
            move_data = self.validate_move(self.selected, q, r)
            if move_data:
                self.apply_move(move_data)
                self.selected = [] # Clear selection after move
                return True
            else:
                # Invalid move, clear selection to be safe or just ignore
                self.selected = []
                return False
        
        return False

    def validate_move(self, selected, target_q, target_r):
        """
        Validate move and return move_data dict if valid, else None.
        move_data: {'type': 'inline'/'broadside', 'dir': (dq, dr), 'marbles': [], 'push_opponent': []}
        """
        if not selected:
            return None
            
        # 1. Determine Direction
        # Target must be adjacent to at least one selected marble (Head)
        # For In-Line: Target is adjacent to the "Head"
        # For Broadside: Target is adjacent to one, and all move in same dir
        
        dq, dr = None, None
        
        # Check if target is neighbor of any selected marble
        neighbor_of = None
        for sq, sr in selected:
            for d in DIRECTIONS:
                if sq + d[0] == target_q and sr + d[1] == target_r:
                    dq, dr = d
                    neighbor_of = (sq, sr)
                    break
            if dq is not None:
                break
                
        if dq is None:
            return None # Target not adjacent
            
        # 2. Classify Move Type
        
        # Check if selection is a line
        is_line = False
        line_dir = None
        
        if len(selected) > 1:
            # Check if they form a line
            # Sort by q then r
            sorted_sel = sorted(selected)
            
            # Check consistency
            # Calculate delta between first two
            d1 = (sorted_sel[1][0] - sorted_sel[0][0], sorted_sel[1][1] - sorted_sel[0][1])
            if d1 in DIRECTIONS:
                # Check if all follow this delta
                valid_line = True
                for i in range(2, len(sorted_sel)):
                    d = (sorted_sel[i][0] - sorted_sel[i-1][0], sorted_sel[i][1] - sorted_sel[i-1][1])
                    if d != d1:
                        valid_line = False
                        break
                if valid_line:
                    is_line = True
                    line_dir = d1
        else:
            is_line = True # Single marble is a line
            line_dir = (dq, dr) # Direction is move direction
            
        # print(f"DEBUG: is_line={is_line}, line_dir={line_dir}, move_dir={(dq, dr)}")

        if not is_line and len(selected) > 1:
             # Should not happen if selection logic enforces adjacency, but for now we assume selection is valid
             # If they are not in a line, they can't move together usually
             return None

        # Broadside: Move direction != Line direction (and > 1 marble)
        if len(selected) > 1 and (dq, dr) != line_dir and (dq, dr) != (-line_dir[0], -line_dir[1]):
            # Broadside
            # Rule: All destination cells must be empty
            for sq, sr in selected:
                tq, tr = sq + dq, sr + dr
                if (tq, tr) in self.grid:
                    return None # Blocked
            
            return {
                'type': 'broadside',
                'dir': (dq, dr),
                'marbles': selected,
                'push_opponent': []
            }
            
        # In-Line: Move direction == Line direction (or opposite)
        else:
            # In-Line
            # Identify Head (closest to target)
            # We already found 'neighbor_of' which is the marble adjacent to target.
            # That is the Head.
            
            # Check if all selected marbles are aligned with the move
            # (Already checked by is_line logic, but need to ensure they are contiguous in the move direction)
            
            # Sort selected marbles based on distance to target (closest first)
            # Distance metric: (q-tq)^2 + (r-tr)^2
            # Actually, just sorting by projection onto direction vector
            
            # Simple approach: The 'neighbor_of' is the head. The others must be behind it.
            # We need to find the chain of marbles starting from Head in -dir.
            
            head = neighbor_of
            chain = [head]
            curr = head
            for _ in range(len(selected) - 1):
                prev = (curr[0] - dq, curr[1] - dr)
                if prev in selected:
                    chain.append(prev)
                    curr = prev
                else:
                    return None # Selected marbles not contiguous in move direction
            
            # Now check target cell
            target_piece = self.grid.get((target_q, target_r))
            
            if not target_piece:
                # Empty -> Valid
                return {
                    'type': 'inline',
                    'dir': (dq, dr),
                    'marbles': chain,
                    'push_opponent': []
                }
            
            elif target_piece.color == self.grid[head].color:
                # Own marble -> Blocked
                return None
                
            else:
                # Opponent -> Sumito Check
                opponent_chain = []
                curr_op = (target_q, target_r)
                
                # Trace opponent line
                while True:
                    p = self.grid.get(curr_op)
                    if p and p.color != self.grid[head].color:
                        opponent_chain.append(curr_op)
                        curr_op = (curr_op[0] + dq, curr_op[1] + dr)
                    else:
                        break
                        
                # Check strength
                if len(chain) <= len(opponent_chain):
                    return None # Too weak
                    
                if len(chain) > 3:
                    return None # Can't push with > 3 (though selection limit is 3)
                    
                # Check cell behind last opponent
                behind_last = curr_op
                p_behind = self.grid.get(behind_last)
                
                if p_behind:
                    return None # Blocked by piece (own or opponent)
                    
                # Valid Push
                return {
                    'type': 'inline',
                    'dir': (dq, dr),
                    'marbles': chain,
                    'push_opponent': opponent_chain
                }

    def apply_move(self, move_data):
        """
        Execute the move.
        """
        dq, dr = move_data['dir']
        
        # 1. Remove all moving marbles from grid first (to avoid overwriting)
        # We need to clear old positions that are not targets of new positions.
        # Actually, let's just do:
        # 1. Remove all involved pieces (own + opponent)
        # 2. Place them in new positions (if on board)
        
        # Collect pieces to move
        pieces_to_move = [] # (piece, new_q, new_r)
        
        # Own
        for mq, mr in move_data['marbles']:
            p = self.grid[(mq, mr)]
            pieces_to_move.append((p, mq + dq, mr + dr))
            del self.grid[(mq, mr)]
            
        # Opponent
        for oq, or_ in move_data['push_opponent']:
            p = self.grid[(oq, or_)]
            pieces_to_move.append((p, oq + dq, or_ + dr))
            del self.grid[(oq, or_)]
            
        # Place pieces
        for p, nq, nr in pieces_to_move:
            if max(abs(nq), abs(nr), abs(-nq-nr)) <= 4:
                self.grid[(nq, nr)] = p
            else:
                # Ejected (Opponent only, own shouldn't be able to suicide usually, but if so, count it?)
                # Rules say you can't push yourself off? Actually you can suicide.
                # If own piece off board -> Opponent score + 1
                if p.color == 'B':
                    self.white_score += 1
                else:
                    self.black_score += 1
                    
        # Check Winner
        if self.white_score >= 6:
            return "White"
        elif self.black_score >= 6:
            return "Black"
            
        return None

    def init_board(self):
        """
        Initialize the standard Abalone board setup.
        """
        self.grid = {}
        
        # White (Top Side)
        # Row r = -4: All 5 cells (q: 0 to 4)
        for q in range(0, 5):
            self.add_piece(q, -4, 'W')
            
        # Row r = -3: All 6 cells (q: -1 to 4)
        for q in range(-1, 5):
            self.add_piece(q, -3, 'W')
            
        # Row r = -2: Middle 3 cells (q: 0, 1, 2)
        for q in range(0, 3):
            self.add_piece(q, -2, 'W')
            
        # Black (Bottom Side)
        # Row r = 4: All 5 cells (q: -4 to 0)
        for q in range(-4, 1):
            self.add_piece(q, 4, 'B')
            
        # Row r = 3: All 6 cells (q: -4 to 1)
        for q in range(-4, 2):
            self.add_piece(q, 3, 'B')
            
        # Row r = 2: Middle 3 cells (q: -2, -1, 0)
        for q in range(-2, 1):
            self.add_piece(q, 2, 'B')
