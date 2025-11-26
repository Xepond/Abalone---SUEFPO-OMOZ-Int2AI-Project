import pygame
import sys
from board_ui import BoardUI
from board import Board
from menu import Menu

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
    
    # Game Board Logic
    game_board = Board()
    game_board.init_board()
    
    current_turn = 'B' # Black starts
    player_color = 'B' # Default
    ai_color = 'W' # Default
    ai_thinking = False
    debug_mode = False
    last_move_str = "-"
    
    game_state = "MENU_HOME" # MENU_HOME, MENU_MODE_SELECT, GAME_RUNNING, GAME_OVER
    winner = None
    
    # Button Rects (will be updated by draw_game_over)
    restart_rect = None
    exit_rect = None
    
    # Menu System
    main_menu = Menu(SCREEN_WIDTH, SCREEN_HEIGHT)
    
    # Notification System
    current_notification = None
    notification_expiry = 0
    
    running = True
    while running:
        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == "GAME_RUNNING":
                        game_state = "MENU_HOME" # Pause/Back to menu?
                    else:
                        running = False
                elif event.key == pygame.K_SPACE:
                    # Manual trigger for test
                    pass
                elif event.key == pygame.K_d:
                    debug_mode = not debug_mode
                    print(f"Debug Mode: {'ON' if debug_mode else 'OFF'}")
            
            # Mouse Events
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    # Block input if animating
                    if board_ui.is_animating:
                        continue
                        
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    
                    if game_state == "MENU_HOME":
                        action = main_menu.handle_home_input(event)
                        if action == "PLAY":
                            game_state = "MENU_MODE_SELECT"
                        elif action == "EXIT":
                            running = False
                            
                    elif game_state == "MENU_MODE_SELECT":
                        action = main_menu.handle_mode_select_input(event)
                        if action == "VS_AI":
                            print("Selected: Play vs AI -> Setup")
                            game_state = "MENU_AI_SETUP"
                        elif action == "LOCAL":
                            print("Selected: Local 2 Players")
                            game_state = "GAME_RUNNING"
                            # Default setup for local
                            game_board.init_board()
                            current_turn = 'B'
                            player_color = 'B' # Both are players really
                            ai_color = None # No AI
                        elif action == "BACK":
                            game_state = "MENU_HOME"
                            
                    elif game_state == "MENU_AI_SETUP":
                        result = main_menu.handle_ai_setup_input(event)
                        if result == "BACK":
                            game_state = "MENU_MODE_SELECT"
                        elif isinstance(result, dict) and result.get("action") == "START":
                            print(f"Starting Game vs AI: {result}")
                            
                            # Determine Player Color
                            player_color_str = result["color"]
                            if "BLACK" in player_color_str:
                                player_color = 'B'
                                ai_color = 'W'
                            else:
                                player_color = 'W'
                                ai_color = 'B'
                                
                            # Initialize Game with AI settings
                            # User is always at BOTTOM, AI at TOP
                            game_board.init_board(top_color=ai_color, bottom_color=player_color)
                            game_board.black_score = 0
                            game_board.white_score = 0
                            
                            # Determine AI Difficulty
                            algo_str = result["algorithm"]
                            ai_depth = 2
                            if "Depth 3" in algo_str:
                                ai_depth = 3
                            elif "Greedy" in algo_str:
                                ai_depth = 1 
                                
                            current_turn = 'B' # Black always starts
                            game_state = "GAME_RUNNING"
                            winner = None
                            last_move_str = "-"
                            
                            # Check if AI starts
                            if ai_color == 'B':
                                ai_thinking = True
                                print("AI (Black) starts thinking...")
                            else:
                                ai_thinking = False
                            
                    elif game_state == "GAME_RUNNING":
                        q, r = board_ui.pixel_to_axial(mouse_x, mouse_y)
                        
                        move_data = None
                        reason = None
                        
                        # Handle click ONLY if it's user's turn
                        if ai_color is None or current_turn == player_color:
                            move_data, reason = game_board.handle_click(q, r, current_turn)
                            
                        if move_data:
                            # Prepare Animation Data
                            anim_data = []
                            dq, dr = move_data['dir']
                            
                            # Own marbles
                            for mq, mr in move_data['marbles']:
                                color = game_board.grid[(mq, mr)].color
                                anim_data.append((color, mq, mr, mq + dq, mr + dr))
                                
                            # Opponent marbles (Push)
                            for oq, or_ in move_data['push_opponent']:
                                color = game_board.grid[(oq, or_)].color
                                anim_data.append((color, oq, or_, oq + dq, or_ + dr))
                                
                            # Start Animation
                            board_ui.start_move_animation(anim_data)
                            
                            # Apply Move (Logical Update)
                            game_board.apply_move(move_data)
                            
                            # Switch turn
                            current_turn = 'W' if current_turn == 'B' else 'B'
                            last_move_str = f"Click at {q},{r}" # Simplified
                            print(f"Move made. Turn: {current_turn}")
                            print(f"Score - Black: {game_board.black_score}, White: {game_board.white_score}")
                            
                            # Check Game Over
                            if game_board.white_score >= 6:
                                game_state = "GAME_OVER"
                                winner = "White"
                                print("White Wins!")
                            elif game_board.black_score >= 6:
                                game_state = "GAME_OVER"
                                winner = "Black"
                                print("Black Wins!")
                                
                            # If vs AI, trigger AI
                            if ai_color is not None and current_turn == ai_color:
                                ai_thinking = True
                                print("AI Turn, thinking...")
                        elif reason:
                            # Invalid move notification
                            current_notification = reason
                            notification_expiry = pygame.time.get_ticks() + 2000
                                
                    elif game_state == "GAME_OVER":
                        # Check buttons
                        if restart_rect and restart_rect.collidepoint(mouse_x, mouse_y):
                            # Restart
                            print("Restarting Game...")
                            game_board.init_board()
                            game_board.black_score = 0
                            game_board.white_score = 0
                            current_turn = 'B'
                            game_state = "GAME_RUNNING"
                            winner = None
                            last_move_str = "-"
                        elif exit_rect and exit_rect.collidepoint(mouse_x, mouse_y):
                            running = False

        # Update Animations
        board_ui.update_animations()
        
        # Ghost Preview Logic
        ghost_positions = []
        ejected_ghost = None
        if game_state == "GAME_RUNNING" and game_board.selected:
            mx, my = pygame.mouse.get_pos()
            hq, hr = board_ui.pixel_to_axial(mx, my)
            
            # Use new method
            ghost_positions, ejected_ghost = game_board.get_ghost_positions(hq, hr)
        
        # Drawing
        screen.fill((0, 0, 0)) # Clear
        
        if game_state == "MENU_HOME":
            main_menu.draw_home(screen)
        elif game_state == "MENU_MODE_SELECT":
            main_menu.draw_mode_select(screen)
        elif game_state == "MENU_AI_SETUP":
            main_menu.draw_ai_setup(screen)
                
        elif game_state in ["GAME_RUNNING", "GAME_OVER"]:
            draw_state = {pos: piece.color for pos, piece in game_board.grid.items()}
            
            ui_data = {
                'current_turn': current_turn,
                'black_score': game_board.black_score,
                'white_score': game_board.white_score,
                'ai_status': 'Ready',
                'last_move': last_move_str
            }
            
            # Determine notification to show
            notify_text = None
            if current_notification and pygame.time.get_ticks() < notification_expiry:
                notify_text = current_notification
            
            board_ui.draw(draw_state, game_board.selected, debug=debug_mode, ui_data=ui_data, ghost_positions=ghost_positions, ghost_color=current_turn, notification_text=notify_text, ejected_ghost=ejected_ghost)
            
            if game_state == "GAME_OVER":
                restart_rect, exit_rect = board_ui.draw_game_over(winner)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
