import pygame

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, text_color=(255, 255, 255)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.is_hovered = False

    def draw(self, screen):
        # Check hover
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Draw Button Rect with Alpha
        current_color = self.hover_color if self.is_hovered else self.color
        
        # Create a surface for transparency
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill(current_color)
        screen.blit(s, self.rect.topleft)
        
        # Draw Border
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=10)
        
        # Draw Text
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class Carousel:
    def __init__(self, x, y, width, height, items, font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.items = items
        self.index = 0
        self.font = pygame.font.SysFont("Arial", font_size, bold=True)
        
        # Arrows
        arrow_size = 30
        self.left_arrow = pygame.Rect(x - arrow_size - 10, y + (height - arrow_size)//2, arrow_size, arrow_size)
        self.right_arrow = pygame.Rect(x + width + 10, y + (height - arrow_size)//2, arrow_size, arrow_size)
        
    def draw(self, screen):
        # Background
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill((30, 30, 30, 150)) # Semi-transparent dark
        screen.blit(s, self.rect.topleft)
        
        # Border
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=10)
        
        # Text
        text = self.items[self.index]
        text_surf = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
        
        # Draw Arrows
        # Left (<)
        pygame.draw.polygon(screen, (200, 200, 200), [
            (self.left_arrow.right, self.left_arrow.top),
            (self.left_arrow.right, self.left_arrow.bottom),
            (self.left_arrow.left, self.left_arrow.centery)
        ])
        
        # Right (>)
        pygame.draw.polygon(screen, (200, 200, 200), [
            (self.right_arrow.left, self.right_arrow.top),
            (self.right_arrow.left, self.right_arrow.bottom),
            (self.right_arrow.right, self.right_arrow.centery)
        ])
        
    def handle_click(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_arrow.collidepoint(event.pos):
                self.index = (self.index - 1) % len(self.items)
                return True
            elif self.right_arrow.collidepoint(event.pos):
                self.index = (self.index + 1) % len(self.items)
                return True
        return False
        
    def get_selected(self):
        return self.items[self.index]

class Menu:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Load Backgrounds
        try:
            self.bg_home = pygame.image.load("assets/main_menu_bg.png").convert()
            self.bg_home = pygame.transform.scale(self.bg_home, (screen_width, screen_height))
        except FileNotFoundError:
            print("Warning: assets/main_menu_bg.png not found.")
            self.bg_home = None
            
        try:
            self.bg_setup = pygame.image.load("assets/selectmode_menu_bg.png").convert()
            self.bg_setup = pygame.transform.scale(self.bg_setup, (screen_width, screen_height))
        except FileNotFoundError:
            print("Warning: assets/selectmode_menu_bg.png not found.")
            self.bg_setup = None
            
        # Initialize Buttons (Bottom Center)
        # PLAY: y = 580, EXIT: y = 650
        cx = screen_width // 2
        btn_width, btn_height = 220, 55
        
        # Transparent/Glass Style: Dark semi-transparent
        btn_color = (30, 30, 30, 150)
        btn_hover = (50, 50, 50, 180)
        
        self.btn_play = Button(cx - btn_width // 2, 550, btn_width, btn_height, "PLAY", btn_color, btn_hover)
        self.btn_exit = Button(cx - btn_width // 2, 620, btn_width, btn_height, "EXIT", btn_color, btn_hover)
        
        # Mode Select Buttons
        self.btn_vs_ai = Button(cx - btn_width // 2, 300, btn_width, btn_height, "Play vs AI", btn_color, btn_hover)
        self.btn_local = Button(cx - btn_width // 2, 370, btn_width, btn_height, "Local 2 Players", btn_color, btn_hover)
        self.btn_back = Button(50, 50, 100, 40, "Back", btn_color, btn_hover) # Top Left
        
        # AI Setup Components
        self.carousel_algo = Carousel(cx - 150, screen_height // 3, 300, 50, ["Greedy", "ID Minimax", "Minimax+ABP"])
        self.carousel_color = Carousel(cx - 150, screen_height // 2 + 50, 300, 50, ["Play as BLACK", "Play as WHITE"])
        self.btn_start = Button(cx - btn_width // 2, screen_height * 2 // 3 + 80, btn_width, btn_height, "START GAME", btn_color, btn_hover)

    def draw_home(self, screen):
        # Draw Background
        if self.bg_home:
            screen.blit(self.bg_home, (0, 0))
        else:
            screen.fill((20, 20, 20))
            
        # Draw Buttons
        self.btn_play.draw(screen)
        self.btn_exit.draw(screen)
        
        # NO Title Text as requested

    def handle_home_input(self, event):
        if self.btn_play.is_clicked(event):
            return "PLAY"
        elif self.btn_exit.is_clicked(event):
            return "EXIT"
        return None

    def draw_mode_select(self, screen):
        # Draw Background (Reuse same bg or darken it?)
        if self.bg_home:
            screen.blit(self.bg_home, (0, 0))
            # Darken for mode select to differentiate?
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))
        else:
            screen.fill((20, 20, 20))
            
        # Draw Buttons
        self.btn_vs_ai.draw(screen)
        self.btn_local.draw(screen)
        self.btn_back.draw(screen)

    def handle_mode_select_input(self, event):
        if self.btn_vs_ai.is_clicked(event):
            return "VS_AI"
        elif self.btn_local.is_clicked(event):
            return "LOCAL"
        elif self.btn_back.is_clicked(event):
            return "BACK"
        return None

    def draw_ai_setup(self, screen):
        # Draw Background
        if self.bg_setup:
            screen.blit(self.bg_setup, (0, 0))
        else:
            screen.fill((20, 20, 20))
            
        # Draw Components
        self.btn_back.draw(screen)
        self.carousel_algo.draw(screen)
        self.carousel_color.draw(screen)
        self.btn_start.draw(screen)
        
        # Labels (Optional, but good for context)
        font = pygame.font.SysFont("Arial", 20, bold=True)
        
        algo_label = font.render("Select Difficulty:", True, (255, 255, 255))
        algo_rect = algo_label.get_rect(center=(self.carousel_algo.rect.centerx, self.carousel_algo.rect.top - 30))
        screen.blit(algo_label, algo_rect)
        
        color_label = font.render("Select Color:", True, (255, 255, 255))
        color_rect = color_label.get_rect(center=(self.carousel_color.rect.centerx, self.carousel_color.rect.top - 30))
        screen.blit(color_label, color_rect)

    def handle_ai_setup_input(self, event):
        if self.btn_back.is_clicked(event):
            return "BACK"
        elif self.btn_start.is_clicked(event):
            return {
                "action": "START",
                "algorithm": self.carousel_algo.get_selected(),
                "color": self.carousel_color.get_selected()
            }
        
        self.carousel_algo.handle_click(event)
        self.carousel_color.handle_click(event)
        
        return None
