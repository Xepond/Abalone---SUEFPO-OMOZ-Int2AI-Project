import matplotlib.pyplot as plt
import time
from board import Board
from ai_engine import AbaloneAI

def run_benchmark():
    """
    Runs the benchmark tests for Greedy, ID Minimax, and Champion AI.
    Returns a dictionary containing the metrics.
    """
    print("Starting Benchmark Suite...")
    results = {}
    
    # Initialize a standard board
    board = Board()
    board.init_board()
    
    # --- Test 1: Greedy Performance ---
    print("\n--- Test 1: Greedy Performance ---")
    ai_greedy = AbaloneAI()
    # Greedy: Depth 1, 3.0s limit (though it's fast), White
    ai_greedy.set_config(algorithm_type="Greedy", max_depth=1, time_limit=3.0, my_color='W')
    
    start_time = time.time()
    ai_greedy.get_best_move(board)
    end_time = time.time()
    
    results['Greedy'] = {
        'nodes_visited': ai_greedy.metrics['nodes_explored'],
        'time': end_time - start_time,
        'depth': 1, # Greedy is always depth 1
        'pruning': 0
    }
    print(f"Greedy: Nodes={results['Greedy']['nodes_visited']}, Time={results['Greedy']['time']:.4f}s")

    # --- Test 2: ID Minimax Performance ---
    print("\n--- Test 2: ID Minimax Performance ---")
    ai_idm = AbaloneAI()
    # ID Minimax: Max Depth 10 (limit by time), 3.0s limit, White
    ai_idm.set_config(algorithm_type="ID Minimax", max_depth=10, time_limit=3.0, my_color='W')
    
    start_time = time.time()
    ai_idm.get_best_move(board)
    end_time = time.time()
    
    results['ID Minimax'] = {
        'nodes_visited': ai_idm.metrics['nodes_explored'],
        'time': ai_idm.metrics['execution_time'], # Use internal metric for consistency
        'depth': ai_idm.metrics['current_depth'],
        'pruning': 0
    }
    print(f"ID Minimax: Nodes={results['ID Minimax']['nodes_visited']}, Depth={results['ID Minimax']['depth']}, Time={results['ID Minimax']['time']:.4f}s")

    # --- Test 3: Champion (Alpha-Beta) Performance ---
    print("\n--- Test 3: Champion (Alpha-Beta) Performance ---")
    ai_champ = AbaloneAI()
    # Champion: Max Depth 10, 3.0s limit (Note: ai_engine might override to 5.0s), White
    ai_champ.set_config(algorithm_type="Minimax+ABP", max_depth=10, time_limit=3.0, my_color='W')
    
    start_time = time.time()
    ai_champ.get_best_move(board)
    end_time = time.time()
    
    results['Champion'] = {
        'nodes_visited': ai_champ.metrics['nodes_explored'],
        'time': ai_champ.metrics['execution_time'],
        'depth': ai_champ.metrics['current_depth'],
        'pruning': ai_champ.metrics['cutoffs']
    }
    print(f"Champion: Nodes={results['Champion']['nodes_visited']}, Depth={results['Champion']['depth']}, Time={results['Champion']['time']:.4f}s, Pruning={results['Champion']['pruning']}")
    
    return results

def plot_graphs(data):
    """
    Generates and saves the benchmark graphs.
    """
    print("\nGenerating Graphs...")
    
    algorithms = ['Greedy', 'ID Minimax', 'Champion']
    colors = ['grey', 'red', 'green']
    
    # --- Graph A: Search Depth Comparison ---
    plt.figure(figsize=(8, 6))
    depths = [data['Greedy']['depth'], data['ID Minimax']['depth'], data['Champion']['depth']]
    
    plt.bar(algorithms, depths, color=colors)
    plt.title("AI Search Depth (3s Limit)")
    plt.ylabel("Depth Reached")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add value labels
    for i, v in enumerate(depths):
        plt.text(i, v + 0.1, str(v), ha='center', fontweight='bold')
        
    plt.savefig('depth_chart.png')
    print("Saved depth_chart.png")
    plt.close()
    
    # --- Graph B: Computational Efficiency (Log Scale) ---
    plt.figure(figsize=(8, 6))
    nodes = [data['Greedy']['nodes_visited'], data['ID Minimax']['nodes_visited'], data['Champion']['nodes_visited']]
    
    plt.bar(algorithms, nodes, color=colors)
    plt.title("Nodes Analyzed vs Pruning Efficiency")
    plt.ylabel("Nodes Visited (Log Scale)")
    plt.yscale('log')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add value labels
    for i, v in enumerate(nodes):
        plt.text(i, v * 1.1, str(v), ha='center', fontweight='bold')
        
    plt.savefig('efficiency_chart.png')
    print("Saved efficiency_chart.png")
    plt.close()
    
    # --- Graph C: Tournament Results (Hardcoded) ---
    plt.figure(figsize=(8, 6))
    labels = ['Champion (3 Wins)', 'Draw (1)', 'IDM (0 Wins)']
    sizes = [3, 1, 0] # Pie chart doesn't like 0, but let's see. 
    # If 0, it won't show. Let's adjust labels or data if needed.
    # Actually, standard pie chart with 0 slice just ignores it.
    # Let's use the raw data: Champion 3, Draw 1, IDM 0.
    
    # To make it look better, maybe exclude 0 from the pie slices but show in legend?
    # Or just pass it.
    
    # Better visualization for 0 wins:
    # Let's just plot the non-zero ones and mention IDM in title or legend.
    # But user asked for "Champion: 3 Wins, Draw: 1, IDM: 0 Wins".
    
    # Let's try passing all.
    sizes_plot = [3, 1]
    labels_plot = ['Champion', 'Draw']
    colors_plot = ['green', 'grey']
    explode = (0.1, 0)  # explode 1st slice
    
    plt.pie(sizes_plot, explode=explode, labels=labels_plot, colors=colors_plot,
            autopct='%1.1f%%', shadow=True, startangle=140)
            
    plt.title("Tournament Results (4 Matches)\n(ID Minimax: 0 Wins)")
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    plt.savefig('tournament_chart.png')
    print("Saved tournament_chart.png")
    plt.close()

if __name__ == "__main__":
    data = run_benchmark()
    plot_graphs(data)
    print("\nBenchmark Suite Completed Successfully.")
