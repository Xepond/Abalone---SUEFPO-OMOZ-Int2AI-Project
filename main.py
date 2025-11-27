import pygame
import sys
from board_ui import BoardUI
from board import Board
from menu import Menu
from ai_engine import AbaloneAI

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
    
    # AI Engine
    ai_engine = AbaloneAI()
    
    current_turn = 'B' # Black starts
    player_color = 'B' # Default
    ai_color = 'W' # Default
    ai_thinking = False
    debug_mode = False
    last_move_str = "-"
    
    # AI Visualization State
    ai_pending_move = None
    ai_move_timer = 0
    ai_visualizing = False
    
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
                    
                    # Check Developer Mode Toggle (Global check if in game)
                    if game_state in ["GAME_RUNNING", "GAME_OVER"]:
                        if board_ui.toggle_rect.collidepoint(mouse_x, mouse_y):
                            board_ui.show_debug_metrics = not board_ui.show_debug_metrics
                            print(f"Developer Mode: {board_ui.show_debug_metrics}")
                            continue # Skip other clicks if toggle clicked
                    
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
                            
                            # Determine AI Difficulty
                            algo_str = result["algorithm"]
                            
                            if "Greedy" not in algo_str and "ID Minimax" not in algo_str:
                                current_notification = "Not Implemented Yet"
                                notification_expiry = pygame.time.get_ticks() + 2000
                                # Do not start game, stay in menu
                            else:
                                if "Greedy" in algo_str:
                                    ai_depth = 1 
                                    ai_algo_type = "Greedy"
                                else:
                                    ai_depth = 1
                                    ai_algo_type = "ID Minimax"
                                
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
                                
                                # Configure AI
                                ai_engine.set_config(ai_algo_type, ai_depth, 3.0, ai_color) 
                                    
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
                            
                            # Record History for Repetition Detection
                            ai_engine.update_history(game_board)
                            
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
        # Only show user ghosts if AI is not visualizing/thinking and it's user's turn (or free play)
        if game_state == "GAME_RUNNING" and game_board.selected and not ai_visualizing and not ai_thinking:
            mx, my = pygame.mouse.get_pos()
            hq, hr = board_ui.pixel_to_axial(mx, my)
            
            # Use new method
            ghost_positions, ejected_ghost = game_board.get_ghost_positions(hq, hr)
            
        # AI Logic Loop (Process while rendering)
        if game_state == "GAME_RUNNING" and ai_thinking and not board_ui.is_animating:
            # For now, we do blocking call. In future, thread this.
            # To allow UI to draw "Thinking...", we might need to do this in a separate thread or 
            # just accept the freeze for now (simple implementation).
            # Let's do a quick draw call before blocking?
            # Actually, Pygame event loop blocks.
            # We'll just call it.
            
            print(f"AI ({ai_engine.algorithm_type}) calculating...")
            
            # Define callback for UI updates during AI search
            last_update_time = [0] # Mutable to persist in closure
            
            def ai_progress_callback():
                current_time = pygame.time.get_ticks()
                if current_time - last_update_time[0] > 100: # 10 FPS update during thinking
                    last_update_time[0] = current_time
                    
                    pygame.event.pump() # Keep OS happy
                    
                    # Redraw
                    screen.fill((0, 0, 0))
                    draw_state = {pos: piece.color for pos, piece in game_board.grid.items()}
                    
                    # We need to reconstruct ui_data with latest metrics
                    ui_data = {
                        'current_turn': current_turn,
                        'black_score': game_board.black_score,
                        'white_score': game_board.white_score,
                        'ai_status': 'Thinking...',
                        'last_move': last_move_str,
                        'ai_metrics': ai_engine.metrics,
                        'ai_algo': ai_engine.algorithm_type
                    }
                    
                    board_ui.draw(draw_state, game_board.selected, debug=debug_mode, ui_data=ui_data, ghost_positions=[])
                    pygame.display.flip()

            best_move = ai_engine.get_best_move(game_board, progress_callback=ai_progress_callback)
            
            if best_move:
                # Start Visualization Phase instead of applying immediately
                ai_pending_move = best_move
                ai_visualizing = True
                ai_move_timer = pygame.time.get_ticks() + 1500 # 1.5 seconds delay
                
                # Highlight AI Selection
                game_board.selected = best_move['marbles']
                
                # Pass ghost positions to board for rendering
                # We need to calculate ghost positions from the move
                # best_move has 'marbles' (list of (q,r)) and 'dir' (dq, dr)
                # We want to show where they WILL be.
                # Or just show the marbles that will move?
                # The prompt says "Show a 'Ghost' of its move".
                # Usually means showing the destination positions.
                
                ghost_positions = []
                dq, dr = best_move['dir']
                for mq, mr in best_move['marbles']:
                    color = game_board.grid[(mq, mr)].color
                    ghost_positions.append((mq + dq, mr + dr, color))
                
                # Also opponent pushed marbles?
                for oq, or_ in best_move['push_opponent']:
                    color = game_board.grid[(oq, or_)].color
                    ghost_positions.append((oq + dq, or_ + dr, color))
                    
                # We need a way to pass this to the main loop's drawing phase
                # But we are inside the loop.
                # We can store it in a variable that persists.
                # Let's use a new variable `ai_ghosts`
                
            else:
                print("AI has no moves! Game Over?")
                current_turn = player_color # Pass turn
                
            ai_thinking = False
            
        # Handle AI Visualization Timer
        ai_ghosts = []
        if game_state == "GAME_RUNNING" and ai_visualizing:
            if pygame.time.get_ticks() >= ai_move_timer:
                # Timer finished, apply move
                best_move = ai_pending_move
                
                # Animate AI move
                anim_data = []
                dq, dr = best_move['dir']
                for mq, mr in best_move['marbles']:
                    color = game_board.grid[(mq, mr)].color
                    anim_data.append((color, mq, mr, mq + dq, mr + dr))
                for oq, or_ in best_move['push_opponent']:
                    color = game_board.grid[(oq, or_)].color
                    anim_data.append((color, oq, or_, oq + dq, or_ + dr))
                    
                board_ui.start_move_animation(anim_data)
                game_board.apply_move(best_move)
                
                # Clear Selection
                game_board.selected = []
                
                # Record History for Repetition Detection
                ai_engine.update_history(game_board)
                
                last_move_str = f"AI: {best_move['type']}"
                current_turn = player_color
                print(f"AI Move: {best_move}")
                
                # Reset State
                ai_visualizing = False
                ai_pending_move = None
                
                # Check Win after AI
                if game_board.white_score >= 6:
                    game_state = "GAME_OVER"
                    winner = "White"
                elif game_board.black_score >= 6:
                    game_state = "GAME_OVER"
                    winner = "Black"
            else:
                # Still waiting, calculate ghosts for drawing
                if ai_pending_move:
                    dq, dr = ai_pending_move['dir']
                    for mq, mr in ai_pending_move['marbles']:
                        color = game_board.grid[(mq, mr)].color
                        ai_ghosts.append((mq + dq, mr + dr, color))
                    for oq, or_ in ai_pending_move['push_opponent']:
                        color = game_board.grid[(oq, or_)].color
                        ai_ghosts.append((oq + dq, or_ + dr, color))
        
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
                'ai_status': 'Thinking...' if ai_thinking else 'Ready',
                'last_move': last_move_str,
                'ai_metrics': ai_engine.metrics,
                'ai_algo': ai_engine.algorithm_type
            }
            
            # Determine notification to show
            notify_text = None
            if current_notification and pygame.time.get_ticks() < notification_expiry:
                notify_text = current_notification
            
            # Combine user ghosts and AI ghosts
            final_ghosts = ghost_positions + ai_ghosts
            
            board_ui.draw(draw_state, game_board.selected, debug=debug_mode, ui_data=ui_data, ghost_positions=final_ghosts, notification_text=notify_text, ejected_ghost=ejected_ghost)
            
            if game_state == "GAME_OVER":
                restart_rect, exit_rect = board_ui.draw_game_over(winner)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
