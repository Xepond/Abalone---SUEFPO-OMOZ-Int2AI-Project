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

class Menu:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Load Background
        try:
            self.bg_image = pygame.image.load("assets/main_menu_bg.png").convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (screen_width, screen_height))
        except FileNotFoundError:
            print("Warning: assets/main_menu_bg.png not found. Using default color.")
            self.bg_image = None
            
        # Initialize Buttons (Bottom Center)
        # PLAY: y = 580, EXIT: y = 650
        cx = screen_width // 2
        btn_width, btn_height = 220, 55
        
        # Transparent/Glass Style: Dark semi-transparent
        btn_color = (30, 30, 30, 150)
        btn_hover = (50, 50, 50, 180)
        
        self.btn_play = Button(cx - btn_width // 2, 550, btn_width, btn_height, "PLAY", btn_color, btn_hover)
        self.btn_exit = Button(cx - btn_width // 2, 620, btn_width, btn_height, "EXIT", btn_color, btn_hover)
        
        # Mode Select Buttons (Keep existing style or update?)
        # Let's keep them simple for now, maybe update positions later.
        # Re-using similar style for consistency
        self.btn_vs_ai = Button(cx - btn_width // 2, 300, btn_width, btn_height, "Play vs AI", btn_color, btn_hover)
        self.btn_local = Button(cx - btn_width // 2, 370, btn_width, btn_height, "Local 2 Players", btn_color, btn_hover)
        self.btn_back = Button(50, screen_height - 80, 100, 40, "Back", btn_color, btn_hover)

    def draw_home(self, screen):
        # Draw Background
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
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
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
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
