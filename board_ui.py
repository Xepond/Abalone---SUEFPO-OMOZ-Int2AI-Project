import pygame
import math

class BoardUI:
    def __init__(self, screen, center_x, center_y, hex_size=30):
        self.screen = screen
        self.cx = center_x
        self.cy = center_y + 60 # Shift board down for UI
        self.hex_size = hex_size
        
        # Load assets
        try:
            self.bg_image = pygame.image.load("assets/wood_table.png").convert()
            self.bg_image = pygame.transform.scale(self.bg_image, self.screen.get_size())
        except FileNotFoundError:
            print("Warning: assets/wood_table.png not found. Using default color.")
            self.bg_image = None

        # Marble setup
        # Hex width (pointy) is sqrt(3)*size. Height is 2*size.
        # We want marbles to fit nicely.
        marble_radius = int(hex_size * 0.85) 
        marble_dim = (marble_radius * 2, marble_radius * 2)
        
        try:
            self.black_marble = pygame.image.load("assets/black_marble.png").convert_alpha()
            self.black_marble = pygame.transform.smoothscale(self.black_marble, marble_dim)
            
            self.white_marble = pygame.image.load("assets/white_marble.png").convert_alpha()
            self.white_marble = pygame.transform.smoothscale(self.white_marble, marble_dim)
        except FileNotFoundError:
            print("Warning: Marble assets not found. Using circles.")
            self.black_marble = None
            self.white_marble = None
        
        self.animations = [] # List of dicts: {key, start, end, color, start_time, duration, on_finish}
        
        # Precompute valid board coordinates (61 cells)
        self.valid_cells = self._generate_valid_cells()
        
        # Fonts
        self.debug_font = pygame.font.SysFont("Arial", 12, bold=True)
        self.ui_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.ui_font_small = pygame.font.SysFont("Arial", 14)

    def _generate_valid_cells(self):
        """
        Generate the set of valid (q, r) coordinates for a standard Abalone board (radius 4).
        Condition: max(abs(q), abs(r), abs(-q-r)) <= 4
        """
        cells = []
        for q in range(-4, 5):
            for r in range(-4, 5):
                if max(abs(q), abs(r), abs(-q-r)) <= 4:
                    cells.append((q, r))
        return cells

    def axial_to_pixel(self, q, r):
        """
        Convert axial coordinates (q, r) to pixel coordinates (x, y).
        Using Pointy-topped hexagon orientation.
        """
        x = self.hex_size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
        y = self.hex_size * (3./2 * r)
        return (x + self.cx, y + self.cy)
        
    def pixel_to_axial(self, x, y):
        """
        Convert pixel coordinates (x, y) to axial coordinates (q, r).
        """
        x = x - self.cx
        y = y - self.cy
        
        q = (math.sqrt(3)/3 * x - 1./3 * y) / self.hex_size
        r = (2./3 * y) / self.hex_size
        
        return self._axial_round(q, r)
        
    def _axial_round(self, q, r):
        """
        Round floating point axial coordinates to nearest integer axial coordinates.
        """
        x, y, z = q, r, -q-r
        rx, ry, rz = round(x), round(y), round(z)
        
        x_diff = abs(rx - x)
        y_diff = abs(ry - y)
        z_diff = abs(rz - z)
        
        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz
        else:
            rz = -rx - ry
            
        return int(rx), int(ry)

    def draw(self, board_state, selected_cells=[], debug=False, ui_data=None):
        """
        Draw the game board and marbles.
        board_state: dict {(q, r): 'B' or 'W'}
        selected_cells: list of (q, r) tuples
        debug: bool, if True draw coordinate labels
        ui_data: dict containing UI info (turn, scores, etc.)
        """
        # Draw Background
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill((30, 30, 30)) # Fallback dark gray

        # Draw UI Elements
        if ui_data:
            self._draw_top_bar(ui_data)
            self._draw_score_panels(ui_data.get('black_score', 0), ui_data.get('white_score', 0))

        # Draw Board Boundary
        self._draw_board_boundary()
        
        # Draw Sockets (Empty cells)
        for q, r in self.valid_cells:
            x, y = self.axial_to_pixel(q, r)
            self._draw_socket(x, y, q, r, debug)
        
        # Identify marbles currently animating to skip drawing their static state
        animating_keys = {anim['key'] for anim in self.animations}
        
        # Draw Static Marbles
        for (q, r), color in board_state.items():
            if (q, r) in animating_keys:
                continue
            
            x, y = self.axial_to_pixel(q, r)
            self._draw_marble(color, x, y, q, r, debug)
            
        # Draw Selection Rings
        for q, r in selected_cells:
            x, y = self.axial_to_pixel(q, r)
            # Draw Cyan/Gold ring
            radius = int(self.hex_size * 0.85)
            pygame.draw.circle(self.screen, (0, 255, 255), (int(x), int(y)), radius, 3)
            
        # Draw Animating Marbles
        current_time = pygame.time.get_ticks()
        for anim in self.animations:
            start_x, start_y = self.axial_to_pixel(*anim['start'])
            end_x, end_y = self.axial_to_pixel(*anim['end'])
            
            # Linear Interpolation
            elapsed = current_time - anim['start_time']
            t = min(elapsed / anim['duration'], 1.0)
            
            curr_x = start_x + (end_x - start_x) * t
            curr_y = start_y + (end_y - start_y) * t
            
            self._draw_marble(anim['color'], curr_x, curr_y) # No debug text for moving marbles

    def _draw_top_bar(self, ui_data):
        """
        Draw the top info bar.
        """
        bar_height = 80
        bar_rect = pygame.Rect(0, 0, self.screen.get_width(), bar_height)
        
        # Semi-transparent background
        s = pygame.Surface((self.screen.get_width(), bar_height), pygame.SRCALPHA)
        s.fill((30, 30, 30, 200))
        self.screen.blit(s, (0, 0))
        
        # Content
        # Turn Indicator
        turn_str = f"Current Turn: {'White' if ui_data.get('current_turn') == 'W' else 'Black'}"
        turn_surf = self.ui_font.render(turn_str, True, (255, 255, 255))
        self.screen.blit(turn_surf, (20, 20))
        
        # Scoreboard
        score_str = f"White: {ui_data.get('white_score', 0)} | Black: {ui_data.get('black_score', 0)}"
        score_surf = self.ui_font.render(score_str, True, (255, 255, 255))
        self.screen.blit(score_surf, (300, 20))
        
        # AI Status
        status_str = f"Status: {ui_data.get('ai_status', 'Ready')}"
        status_surf = self.ui_font_small.render(status_str, True, (200, 200, 200))
        self.screen.blit(status_surf, (20, 50))
        
        # Last Move
        move_str = f"Last Move: {ui_data.get('last_move', '-')}"
        move_surf = self.ui_font_small.render(move_str, True, (200, 200, 200))
        self.screen.blit(move_surf, (300, 50))

    def _draw_score_panels(self, black_score, white_score):
        """
        Draw captured marble slots in 2x3 grid panels.
        """
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        
        # Panel 1: Top Player's Graveyard (AI/P2 - White)
        # Position: Top-Left, x=30, y=120
        # Content: Captured Black marbles
        self._draw_panel(30, 120, white_score, 'B', "P2: White")
        
        # Panel 2: Bottom Player's Graveyard (User/P1 - Black)
        # Position: Bottom-Right, x=Width-230, y=Height-160
        # Content: Captured White marbles
        self._draw_panel(screen_w - 230, screen_h - 160, black_score, 'W', "P1: Black")

    def _draw_panel(self, x, y, captured_count, marble_color, label=""):
        """
        Draw a single score panel.
        """
        width, height = 200, 150 # Increased height
        
        # Background Box
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        s.fill((30, 30, 30, 180))
        self.screen.blit(s, (x, y))
        
        # Border
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (100, 100, 100), rect, 2, border_radius=10)
        
        # Label
        if label:
            # Use Bold UI Font, Bright White
            text_surf = self.ui_font.render(label, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(x + width // 2, y + 20)) # Centered at top
            self.screen.blit(text_surf, text_rect)
        
        # 2x3 Grid
        # Marble size (diameter) = 30px (radius 15)
        marble_radius = 15
        col_spacing = 45
        row_spacing = 45
        
        # Calculate Grid Dimensions
        # Width = (cols-1)*spacing + diameter = 2*45 + 30 = 120
        grid_width = 120
        
        # Center Grid Horizontally
        # Start X (Left edge of grid)
        grid_start_x = x + (width - grid_width) // 2
        
        # Vertical Position
        # Start Y (Top edge of grid) - Push down to y + 50 to clear text
        grid_start_y = y + 50
        
        for i in range(6):
            row = i // 3
            col = i % 3
            
            # Center of marble
            mx = grid_start_x + marble_radius + col * col_spacing
            my = grid_start_y + marble_radius + row * row_spacing
            
            # Draw socket
            pygame.draw.circle(self.screen, (50, 50, 50), (mx, my), marble_radius)
            
            # Draw marble if captured
            if i < captured_count:
                self._draw_marble_icon(marble_color, mx, my)

    def draw_game_over(self, winner):
        """
        Draw Game Over overlay and buttons.
        Returns (restart_rect, exit_rect)
        """
        # Overlay
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        cx, cy = self.screen.get_width() // 2, self.screen.get_height() // 2
        
        # Game Over Text
        go_surf = self.ui_font.render("GAME OVER", True, (255, 255, 255))
        go_rect = go_surf.get_rect(center=(cx, cy - 100))
        self.screen.blit(go_surf, go_rect)
        
        # Winner Text
        win_surf = self.ui_font.render(f"{winner.upper()} WINS!", True, (255, 215, 0)) # Gold color
        win_rect = win_surf.get_rect(center=(cx, cy - 50))
        self.screen.blit(win_surf, win_rect)
        
        # Buttons
        btn_width, btn_height = 200, 50
        spacing = 20
        
        # Restart Button
        restart_rect = pygame.Rect(0, 0, btn_width, btn_height)
        restart_rect.center = (cx, cy + 50)
        
        # Exit Button
        exit_rect = pygame.Rect(0, 0, btn_width, btn_height)
        exit_rect.center = (cx, cy + 50 + btn_height + spacing)
        
        # Draw Buttons
        self._draw_button(restart_rect, "RESTART")
        self._draw_button(exit_rect, "EXIT")
        
        return restart_rect, exit_rect

    def _draw_button(self, rect, text):
        """
        Helper to draw a menu-style button.
        """
        # Background
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill((50, 50, 50, 200))
        self.screen.blit(s, rect.topleft)
        
        # Border
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=5)
        
        # Text
        txt_surf = self.ui_font.render(text, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)

    def _draw_marble_icon(self, color, x, y):
        """
        Helper to draw a small marble icon.
        """
        img = self.black_marble if color == 'B' else self.white_marble
        if img:
            # Scale down for graveyard
            scaled = pygame.transform.smoothscale(img, (30, 30))
            rect = scaled.get_rect(center=(x, y))
            self.screen.blit(scaled, rect)
        else:
            c = (0, 0, 0) if color == 'B' else (255, 255, 255)
            pygame.draw.circle(self.screen, c, (x, y), 15)

    def _draw_board_boundary(self):
        """
        Draw a polygon outlining the board.
        The board is a hexagon. We can approximate it by drawing a large filled hexagon 
        behind the cells.
        """
        # Calculate corners of the board (radius 4.5 hex size roughly to cover cells)
        # Or better, use the 6 corner cells and extend outwards.
        # Corner cells: (0, -4), (4, -4), (4, 0), (0, 4), (-4, 4), (-4, 0)
        
        corners = [
            (0, -4), (4, -4), (4, 0), (0, 4), (-4, 4), (-4, 0)
        ]
        
        # We want the boundary to be slightly outside the center of these cells.
        # The distance from center to cell center is 4 * hex_width (approx).
        # Let's just draw a large regular hexagon.
        
        # Radius in pixels for the background hexagon
        # 5 cells side length.
        # Distance to corner cell center is roughly 4.5 * hex_size * sqrt(3)? No.
        # Let's compute pixel coords of corners and extend them.
        
        poly_points = []
        offset = self.hex_size * 1.0 # Extend by 1 hex size
        
        # Actually, let's just use a large circle or hexagon for the base.
        # Abalone board is usually hexagonal.
        
        # Let's calculate the 6 vertices of the board boundary.
        # It's a hexagon rotated 30 degrees (pointy top) or flat top?
        # Our cells are pointy topped. The board itself is a hexagon.
        # The board edges are parallel to the cell edges?
        # Yes.
        
        # Let's manually define the 6 vertices relative to center.
        # Radius of the board (center to vertex) is roughly (4 + 0.5) * hex_height?
        # Let's try drawing a polygon connecting the outer points of the corner cells.
        
        # Corner cells:
        # Top Left: (0, -4)
        # Top Right: (4, -4)
        # Right: (4, 0)
        # Bottom Right: (0, 4)
        # Bottom Left: (-4, 4)
        # Left: (-4, 0)
        
        # For each corner cell, we want the vertex of that cell that is furthest from center.
        # (0, -4) -> Top Left. Furthest point is its Top Left vertex?
        # Actually, let's just draw a big dark hexagon.
        
        board_radius = self.hex_size * 8.0 # Adjusted radius to fit tightly
        
        # Draw a filled hexagon
        points = []
        for i in range(6):
            angle_deg = 60 * i # Flat-topped to match grid
            angle_rad = math.radians(angle_deg)
            px = self.cx + board_radius * math.cos(angle_rad)
            py = self.cy + board_radius * math.sin(angle_rad)
            points.append((px, py))
            
        # Draw board base (Dark Anthracite)
        pygame.draw.polygon(self.screen, (40, 40, 40), points)
        
        # Draw border (Lighter Gray, Thicker)
        pygame.draw.polygon(self.screen, (70, 70, 70), points, 8)

    def _draw_socket(self, x, y, q=0, r=0, debug=False):
        """
        Draw a socket/groove at x, y.
        """
        # Draw a solid filled circle
        radius = int(self.hex_size * 0.8)
        pygame.draw.circle(self.screen, (60, 60, 70), (int(x), int(y)), radius)
        
        if debug:
            text_surf = self.debug_font.render(f"{q},{r}", True, (150, 150, 150))
            text_rect = text_surf.get_rect(center=(int(x), int(y)))
            self.screen.blit(text_surf, text_rect)

    def _draw_marble(self, color, x, y, q=0, r=0, debug=False):
        img = self.black_marble if color == 'B' else self.white_marble
        if img:
            rect = img.get_rect(center=(x, y))
            self.screen.blit(img, rect)
        else:
            # Fallback drawing
            c = (0, 0, 0) if color == 'B' else (255, 255, 255)
            pygame.draw.circle(self.screen, c, (int(x), int(y)), int(self.hex_size * 0.8))
            
        if debug:
            text_color = (255, 255, 255) if color == 'B' else (0, 0, 0)
            text_surf = self.debug_font.render(f"{q},{r}", True, text_color)
            text_rect = text_surf.get_rect(center=(int(x), int(y)))
            self.screen.blit(text_surf, text_rect)

    def start_animation(self, start_qr, end_qr, color, on_finish_callback=None, duration=200):
        """
        Start moving a marble from start_qr to end_qr.
        """
        self.animations.append({
            'key': start_qr, # Hide the marble at the start position
            'start': start_qr,
            'end': end_qr,
            'color': color,
            'start_time': pygame.time.get_ticks(),
            'duration': duration,
            'on_finish': on_finish_callback
        })

    def update_animations(self):
        """
        Update animation states and trigger callbacks for finished animations.
        """
        current_time = pygame.time.get_ticks()
        finished = []
        active = []
        
        for anim in self.animations:
            if current_time - anim['start_time'] >= anim['duration']:
                finished.append(anim)
            else:
                active.append(anim)
        
        self.animations = active
        
        for anim in finished:
            if anim['on_finish']:
                anim['on_finish']()
