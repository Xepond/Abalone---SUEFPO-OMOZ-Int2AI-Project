import pygame
import sys
from board_ui import BoardUI
from board import Board

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
HEX_SIZE = 30
FPS = 60

def main():
    pygame.init()
    
    # Set Window Icon
    try:
        icon_surface = pygame.image.load("assets/icon.png")
        pygame.display.set_icon(icon_surface)
    except Exception as e:
        print(f"Warning: Could not load icon: {e}")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Abalone - SUEFPO OMOZ Int2AI Project")
    clock = pygame.time.Clock()

    # Center the board
    board_ui = BoardUI(screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, HEX_SIZE)
    
    # Game State
    game_board = Board()
    game_board.init_board()
    
    current_turn = 'B' # Black starts
    debug_mode = False
    last_move_str = "-"
    
    game_state = "RUNNING" # RUNNING, GAME_OVER
    winner = None
    
    # Button Rects (will be updated by draw_game_over)
    restart_rect = None
    exit_rect = None
    
    running = True
    while running:
        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Manual trigger for test
                    pass
                elif event.key == pygame.K_d:
                    debug_mode = not debug_mode
                    print(f"Debug Mode: {'ON' if debug_mode else 'OFF'}")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    
                    if game_state == "RUNNING":
                        q, r = board_ui.pixel_to_axial(mouse_x, mouse_y)
                        
                        # Handle click
                        move_made = game_board.handle_click(q, r, current_turn)
                        
                        if move_made:
                            # Switch turn
                            current_turn = 'W' if current_turn == 'B' else 'B'
                            last_move_str = f"Click at {q},{r}" # Simplified
                            print(f"Move made. Turn: {current_turn}")
                            print(f"Score - Black: {game_board.black_score}, White: {game_board.white_score}")
                            
                            # Check Game Over (Winner returned by apply_move, but apply_move was called inside handle_click)
                            # Wait, handle_click calls apply_move. apply_move returns winner now.
                            # But handle_click returns True/False.
                            # We need to update handle_click to propagate the winner or check board state here.
                            # Actually, let's just check board scores here or update handle_click.
                            # Checking scores here is safer as apply_move return value is lost in handle_click.
                            
                            if game_board.white_score >= 6:
                                game_state = "GAME_OVER"
                                winner = "White"
                                print("White Wins!")
                            elif game_board.black_score >= 6:
                                game_state = "GAME_OVER"
                                winner = "Black"
                                print("Black Wins!")
                                
                    elif game_state == "GAME_OVER":
                        # Check buttons
                        if restart_rect and restart_rect.collidepoint(mouse_x, mouse_y):
                            # Restart
                            print("Restarting Game...")
                            game_board.init_board()
                            game_board.black_score = 0
                            game_board.white_score = 0
                            current_turn = 'B'
                            game_state = "RUNNING"
                            winner = None
                            last_move_str = "-"
                        elif exit_rect and exit_rect.collidepoint(mouse_x, mouse_y):
                            running = False

        # Update Animations
        board_ui.update_animations()
        
        # Drawing
        draw_state = {pos: piece.color for pos, piece in game_board.grid.items()}
        
        ui_data = {
            'current_turn': current_turn,
            'black_score': game_board.black_score,
            'white_score': game_board.white_score,
            'ai_status': 'Ready',
            'last_move': last_move_str
        }
        
        board_ui.draw(draw_state, game_board.selected, debug=debug_mode, ui_data=ui_data)
        
        if game_state == "GAME_OVER":
            restart_rect, exit_rect = board_ui.draw_game_over(winner)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
