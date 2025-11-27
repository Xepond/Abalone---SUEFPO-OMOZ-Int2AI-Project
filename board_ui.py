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

        # Developer Mode Assets
        self.show_debug_metrics = False
        self.toggle_rect = pygame.Rect(self.screen.get_width() - 160, 10, 140, 30)
        try:
            self.dev_bg_image = pygame.image.load("assets/dev_mode_bg.png").convert()
            self.dev_bg_image = pygame.transform.scale(self.dev_bg_image, self.screen.get_size())
        except FileNotFoundError:
            print("Warning: assets/dev_mode_bg.png not found.")
            self.dev_bg_image = None

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
        self.is_animating = False
        
        # Precompute valid board coordinates (61 cells)
        self.valid_cells = self._generate_valid_cells()
        
        # Fonts
        self.debug_font = pygame.font.SysFont("Arial", 12, bold=True)
        self.ui_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.ui_font_small = pygame.font.SysFont("Arial", 14)

    def start_move_animation(self, move_anim_data):
        """
        Start animations for a move.
        move_anim_data: List of tuples (color, start_q, start_r, end_q, end_r)
        """
        self.animations = []
        current_time = pygame.time.get_ticks()
        duration = 250 # ms
        
        for color, sq, sr, eq, er in move_anim_data:
            self.animations.append({
                'key': (eq, er), # The destination cell (to hide static marble)
                'start': (sq, sr),
                'end': (eq, er),
                'color': color,
                'start_time': current_time,
                'duration': duration
            })
            
        self.is_animating = True

    def update_animations(self):
        """
        Update animation progress.
        """
        if not self.is_animating:
            return
            
        current_time = pygame.time.get_ticks()
        active_anims = []
        
        for anim in self.animations:
            elapsed = current_time - anim['start_time']
            if elapsed < anim['duration']:
                active_anims.append(anim)
        
        self.animations = active_anims
        
        if not self.animations:
            self.is_animating = False

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

    def draw(self, board_state, selected_cells=None, debug=False, ui_data=None, ghost_positions=None, ghost_color=None, notification_text=None, ejected_ghost=None):
        """
        Main draw function.
        board_state: dict {(q, r): color_char}
        selected_cells: list of (q, r)
        ui_data: dict with 'current_turn', 'black_score', 'white_score', 'ai_status', 'last_move'
        ghost_positions: list of (q, r) for ghost marbles
        ghost_color: 'B' or 'W'
        notification_text: String to display as toast message
        ejected_ghost: (q, r) tuple if a marble is ejected
        """
        # Draw Background
        if self.show_debug_metrics and self.dev_bg_image:
            self.screen.blit(self.dev_bg_image, (0, 0))
        elif self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill((30, 30, 30)) # Fallback dark gray

        # Draw UI Elements
        if ui_data:
            self._draw_top_bar(ui_data)
            self._draw_score_panels(ui_data.get('black_score', 0), ui_data.get('white_score', 0))
            
        # Draw Developer Mode Toggle
        self._draw_toggle_switch()
        
        # Draw Dashboard if enabled
        if self.show_debug_metrics and ui_data:
            self._draw_dashboard(ui_data)

        # Draw Board Boundary
        self._draw_board_boundary()
        
        # Draw Sockets (Grid)
        for q, r in self.valid_cells:
            x, y = self.axial_to_pixel(q, r)
            self._draw_socket(x, y, q, r, debug)
        
        # Draw Ghosts
        if ghost_positions or ejected_ghost:
            self.draw_ghosts(ghost_positions, ejected_ghost)

        # Identify marbles currently animating to skip drawing their static state
        animating_keys = {anim['key'] for anim in self.animations}
        
        # Draw Static Marbles
        for (q, r), color in board_state.items():
            if (q, r) in animating_keys:
                continue
            
            x, y = self.axial_to_pixel(q, r)
            self._draw_marble(color, x, y, q, r, debug)
            
        # Draw Selection Rings
        # Renders selection highlight for both Human and AI (when board.selected is set)
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

        # Draw Notification Toast
        if notification_text:
            self.draw_notification(notification_text)

    def draw_notification(self, text):
        """
        Draw a toast notification at the bottom of the screen.
        """
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        
        # Render text
        text_surf = self.ui_font.render(text, True, (255, 255, 255))
        padding_x, padding_y = 20, 10
        width = text_surf.get_width() + padding_x * 2
        height = text_surf.get_height() + padding_y * 2
        
        # Position: Bottom Center
        x = (screen_w - width) // 2
        y = screen_h - 100
        
        # Background Rect
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        s.fill((50, 0, 0, 200)) # Semi-transparent Dark Red
        
        # Draw rounded rect on screen
        # Since we want rounded corners with alpha, we can blit the surface then draw border?
        # Or just draw rect on surface?
        # Pygame's draw.rect supports border_radius on the target surface directly.
        
        # Let's draw directly on screen for simplicity with alpha
        # Create a surface for the background
        bg_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (80, 0, 0, 220), bg_surf.get_rect(), border_radius=10)
        
        self.screen.blit(bg_surf, (x, y))
        
        # Blit text
        text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surf, text_rect)

    def draw_ghosts(self, ghost_positions, ejected_ghost=None):
        """
        Draw semi-transparent ghost marbles.
        ghost_positions: List of (q, r, color)
        """
        for q, r, color in ghost_positions:
            img = self.black_marble if color == 'B' else self.white_marble
            if not img:
                continue
                
            # Create ghost image with alpha
            ghost_img = img.copy()
            ghost_img.set_alpha(135) 
            
            x, y = self.axial_to_pixel(q, r)
            
            # Draw Ghost Marble
            rect = ghost_img.get_rect(center=(x, y))
            self.screen.blit(ghost_img, rect)
            
            # Ring surface for Black marble fallback (faint white outline)
            if color == 'B':
                radius = int(self.hex_size * 0.85)
                surf_size = radius * 2 + 4
                ring_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (200, 200, 200, 80), (surf_size // 2, surf_size // 2), radius, 1)
                ring_rect = ring_surf.get_rect(center=(x, y))
                self.screen.blit(ring_surf, ring_rect)

        # Draw Ejected Ghost (if any)
        if ejected_ghost:
            q, r = ejected_ghost
            x, y = self.axial_to_pixel(q, r)
            
            # Draw Ghost Marble (Opponent color usually, but here we just use the passed color? 
            # Wait, if I push opponent, the ghost should be opponent color.
            # But the 'color' arg is 'current_turn'.
            # If I push opponent, the ejected piece is opponent's.
            # So we should probably switch color for ejected ghost if it's opponent.
            # But for now, let's just use the ghost_img. 
            # Actually, if I push White as Black, the ejected ghost should be White.
            # Let's check logic in main.py. We pass ghost_color=current_turn.
            # We might need to handle color better. 
            # But the prompt says "Draw the semi-transparent ghost marble... Draw Red X".
            # Let's stick to the prompt. It implies using the same ghost style.
            # But logically it should be the opponent's color.
            # Let's try to infer color. If current_turn is 'B', ejected is 'W'.
            
            ejected_color = 'W' if color == 'B' else 'B'
            e_img = self.black_marble if ejected_color == 'B' else self.white_marble
            if e_img:
                e_ghost = e_img.copy()
                e_ghost.set_alpha(135)
                rect = e_ghost.get_rect(center=(x, y))
                self.screen.blit(e_ghost, rect)
            
            # Draw Red X
            # Radius
            R = int(self.hex_size * 0.85)
            # Line 1
            pygame.draw.line(self.screen, (200, 0, 0), (x - R/2, y - R/2), (x + R/2, y + R/2), 4)
            # Line 2
            pygame.draw.line(self.screen, (200, 0, 0), (x + R/2, y - R/2), (x - R/2, y + R/2), 4)

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
        self._draw_panel(30, 120, white_score, 'B', "P2: White Captured")
        
        # Panel 2: Bottom Player's Graveyard (User/P1 - Black)
        # Position: Bottom-Right, x=Width-230, y=Height-160
        # Content: Captured White marbles
        self._draw_panel(screen_w - 230, screen_h - 160, black_score, 'W', "P1: Black Captured")

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



    def _draw_toggle_switch(self):
        """
        Draw the Developer Mode toggle switch.
        """
        # Background
        color = (0, 200, 0) if self.show_debug_metrics else (100, 100, 100)
        pygame.draw.rect(self.screen, color, self.toggle_rect, border_radius=15)
        
        # Knob
        knob_x = self.toggle_rect.right - 25 if self.show_debug_metrics else self.toggle_rect.left + 5
        knob_rect = pygame.Rect(knob_x, self.toggle_rect.top + 5, 20, 20)
        pygame.draw.ellipse(self.screen, (255, 255, 255), knob_rect)
        
        # Label
        label = "DEV MODE"
        text_surf = self.debug_font.render(label, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(self.toggle_rect.centerx, self.toggle_rect.bottom + 10))
        self.screen.blit(text_surf, text_rect)

    def _draw_dashboard(self, ui_data):
        """
        Draw the metrics dashboard on the right side.
        """
        metrics = ui_data.get('ai_metrics', {})
        algo = ui_data.get('ai_algo', 'Unknown')
        
        panel_w = 250
        panel_h = 400
        x = self.screen.get_width() - panel_w - 20
        y = 100
        
        # Panel Background
        s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s.fill((0, 20, 40, 230)) # Dark Blue semi-transparent
        self.screen.blit(s, (x, y))
        
        # Border
        pygame.draw.rect(self.screen, (0, 255, 255), (x, y, panel_w, panel_h), 2)
        
        # Title
        title_surf = self.ui_font.render(f"AI METRICS ({algo})", True, (0, 255, 255))
        self.screen.blit(title_surf, (x + 10, y + 10))
        
        curr_y = y + 50
        line_height = 25
        
        def draw_line(label, value, color=(200, 200, 200)):
            nonlocal curr_y
            lbl_surf = self.ui_font_small.render(f"{label}:", True, (150, 150, 150))
            val_surf = self.ui_font_small.render(str(value), True, color)
            self.screen.blit(lbl_surf, (x + 10, curr_y))
            self.screen.blit(val_surf, (x + 150, curr_y))
            curr_y += line_height

        # Common Metrics
        draw_line("Exec Time", f"{metrics.get('execution_time', 0):.4f}s")
        
        if algo == "Greedy":
            curr_y += 10
            header_surf = self.ui_font.render("Score Breakdown", True, (255, 200, 0))
            self.screen.blit(header_surf, (x + 10, curr_y))
            curr_y += 30
            
            breakdown = metrics.get('last_move_breakdown', {})
            if breakdown:
                draw_line("Material", f"{breakdown.get('Material', 0):.1f}")
                draw_line("Aggression", f"{breakdown.get('Aggression', 0):.1f}")
                draw_line("Cohesion", f"{breakdown.get('Cohesion', 0):.1f}")
                draw_line("Center", f"{breakdown.get('Center', 0):.1f}")
                draw_line("Danger", f"{breakdown.get('Danger', 0):.1f}", (255, 100, 100))
                
                if 'Repetition' in breakdown:
                     draw_line("Repetition", f"{breakdown.get('Repetition', 0):.1f}", (255, 0, 0))

                curr_y += 10
                draw_line("TOTAL", f"{breakdown.get('Total', 0):.1f}", (0, 255, 0))
            else:
                draw_line("Status", "No Move Yet")
                
        elif algo in ["ID Minimax", "IDS"]:
            draw_line("Depth Reached", metrics.get('current_depth', 0))
            draw_line("Nodes Visited", metrics.get('nodes_explored', 0))
            
            # Progress Bar for Time
            curr_y += 20
            bar_w = 200
            bar_h = 10
            pygame.draw.rect(self.screen, (50, 50, 50), (x + 25, curr_y, bar_w, bar_h))
            
            limit = 3.0
            elapsed = metrics.get('time_elapsed', 0)
            progress = min(elapsed / limit, 1.0)
            fill_w = int(progress * bar_w)
            
            if progress < 0.5:
                bar_color = (0, 255, 0)
            elif progress < 0.8:
                bar_color = (255, 255, 0)
            else:
                bar_color = (255, 50, 50)
                
            pygame.draw.rect(self.screen, bar_color, (x + 25, curr_y, fill_w, bar_h))
            
            lbl = self.ui_font_small.render(f"Time: {elapsed:.1f}s", True, (150, 150, 150))
            self.screen.blit(lbl, (x + 25, curr_y - 15))
            
            # Evolution History Table
            curr_y += 20
            hist_header = self.ui_font_small.render("Evolution History", True, (255, 200, 0))
            self.screen.blit(hist_header, (x + 10, curr_y))
            curr_y += 20
            
            # Table Headers
            h1 = self.ui_font_small.render("Depth", True, (150, 150, 150))
            h2 = self.ui_font_small.render("Score", True, (150, 150, 150))
            self.screen.blit(h1, (x + 10, curr_y))
            self.screen.blit(h2, (x + 100, curr_y))
            curr_y += 15
            
            history = metrics.get('depth_history', [])
            # Show last 5 entries
            for d, s in history[-5:]:
                d_surf = self.ui_font_small.render(str(d), True, (200, 200, 200))
                s_surf = self.ui_font_small.render(f"{s:.1f}", True, (200, 200, 200))
                self.screen.blit(d_surf, (x + 10, curr_y))
                self.screen.blit(s_surf, (x + 100, curr_y))
                curr_y += 15
            
        elif algo == "Minimax+ABP":
            draw_line("Depth Reached", metrics.get('current_depth', 0))
            draw_line("Nodes Visited", metrics.get('nodes_explored', 0))
            draw_line("Pruning Count", metrics.get('cutoffs', 0), (255, 100, 100))
            draw_line("Cache Hits", metrics.get('cache_hits', 0), (100, 255, 100))
            
            # Progress Bar for Time
            curr_y += 20
            bar_w = 200
            bar_h = 10
            pygame.draw.rect(self.screen, (50, 50, 50), (x + 25, curr_y, bar_w, bar_h))
            
            limit = 5.0 # 5s for Champion
            elapsed = metrics.get('time_elapsed', 0)
            progress = min(elapsed / limit, 1.0)
            fill_w = int(progress * bar_w)
            
            if progress < 0.5:
                bar_color = (0, 255, 0)
            elif progress < 0.8:
                bar_color = (255, 255, 0)
            else:
                bar_color = (255, 50, 50)
                
            pygame.draw.rect(self.screen, bar_color, (x + 25, curr_y, fill_w, bar_h))
            
            lbl = self.ui_font_small.render(f"Time: {elapsed:.1f}s", True, (150, 150, 150))
            self.screen.blit(lbl, (x + 25, curr_y - 15))

        elif algo == "Minimax":
            draw_line("Depth", metrics.get('depth_reached', 3)) # Fixed depth usually
            draw_line("Nodes Visited", metrics.get('nodes_explored', 0))
            draw_line("Pruning Count", metrics.get('cutoffs', 0), (255, 100, 100))
            draw_line("Cache Hits", metrics.get('cache_hits', 0), (100, 255, 100))
