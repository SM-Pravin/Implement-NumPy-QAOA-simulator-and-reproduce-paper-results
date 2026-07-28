import numpy as np
import time
from scipy.optimize import minimize
from qaoa_simulator import run_qaoa_on_subgraph

# Define subgraphs for p=1 on 3-regular graphs
# g4: 4 vertices. Edges = [(1,2), (0,1), (0,2), (1,3), (2,3)]. Target edge = (1,2)
edges_g4 = [(1, 2), (0, 1), (0, 2), (1, 3), (2, 3)]
n_g4 = 4

# g5: 5 vertices. Edges = [(1,2), (0,1), (0,2), (1,3), (2,4)]. Target edge = (1,2)
edges_g5 = [(1, 2), (0, 1), (0, 2), (1, 3), (2, 4)]
n_g5 = 5

# g6: 6 vertices. Edges = [(1,2), (0,1), (1,3), (2,4), (2,5)]. Target edge = (1,2)
edges_g6 = [(1, 2), (0, 1), (1, 3), (2, 4), (2, 5)]
n_g6 = 6

# Define the 14-vertex tree subgraph for p=2 (equation 36)
# Vertices: 0 to 13
# Target edge: (1, 2)
# Edges:
# - Middle edge: (1, 2)
# - j=1 tree: (1, 0), (1, 3), (0, 4), (0, 5), (3, 6), (3, 7)
# - k=2 tree: (2, 8), (2, 9), (8, 10), (8, 11), (9, 12), (9, 13)
edges_tree14 = [
    (1, 2),
    (1, 0), (1, 3),
    (0, 4), (0, 5),
    (3, 6), (3, 7),
    (2, 8), (2, 9),
    (8, 10), (8, 11),
    (9, 12), (9, 13)
]
n_tree14 = 14

def evaluate_subgraphs_p1(gamma1, beta1):
    """
    Evaluates the expectation values of the target edge for g4, g5, and g6 for p=1.
    """
    g = [gamma1]
    b = [beta1]
    f4 = run_qaoa_on_subgraph(edges_g4, (1, 2), n_g4, g, b)
    f5 = run_qaoa_on_subgraph(edges_g5, (1, 2), n_g5, g, b)
    f6 = run_qaoa_on_subgraph(edges_g6, (1, 2), n_g6, g, b)
    return f4, f5, f6

def get_F1_max(s, t, num_restarts=15):
    """
    Finds the maximum of F1(gamma, beta, s, t) over (gamma, beta) for a given (s, t).
    """
    def objective(params):
        gamma1, beta1 = params[0], params[1]
        f4, f5, f6 = evaluate_subgraphs_p1(gamma1, beta1)
        F1 = s * f4 + (4*s + 3*t) * f5 + (1.5 - 5*s - 3*t) * f6
        return -F1
        
    bounds = [(0, 2*np.pi), (0, np.pi)]
    best_val = -1
    best_params = None
    
    for _ in range(num_restarts):
        init_params = [np.random.uniform(0, 2*np.pi), np.random.uniform(0, np.pi)]
        res = minimize(objective, init_params, bounds=bounds, method='L-BFGS-B')
        val = -res.fun
        if val > best_val:
            best_val = val
            best_params = res.x
            
    return best_val, best_params

def run_reproduction():
    print("="*60)
    print("REPRODUCING 3-REGULAR GRAPH RESULTS (SECTION V)")
    print("="*60)
    
    # 1. Evaluate worst-case ratio for p=1
    print("\n--- 1. Evaluating worst-case approximation ratio for p=1 ---")
    
    # Let's optimize at the vertices of the domain (s, t) where 4s + 3t <= 1:
    # (s=0, t=0), (s=0.25, t=0), (s=0, t=1/3) and a grid of interior points.
    test_points = [
        (0.0, 0.0, "s=0, t=0 (Pure Tree/Generic)"),
        (0.25, 0.0, "s=0.25, t=0 (Max Crossed Squares)"),
        (0.0, 1.0/3.0, "s=0, t=1/3 (Max Isolated Triangles)"),
        (0.1, 0.1, "s=0.1, t=0.1 (Interior)")
    ]
    
    for s, t, desc in test_points:
        best_val, best_params = get_F1_max(s, t, num_restarts=20)
        # The approximation ratio is F1_max / (1.5 - s - t)
        denom = 1.5 - s - t
        ratio = best_val / denom
        print(f"Point: {desc}")
        print(f"  s = {s:.4f}, t = {t:.4f}")
        print(f"  Max Expectation F1 = {best_val:.6f}")
        print(f"  Optimal angles: gamma1 = {best_params[0]:.6f}, beta1 = {best_params[1]:.6f}")
        print(f"  Approximation Ratio = {ratio:.6f}")
        print()

    # Now let's do a grid search over s, t to confirm the minimum is at s=t=0
    print("Running grid search over (s, t) to find the minimum approximation ratio...")
    grid_size = 11
    s_vals = np.linspace(0, 0.25, grid_size)
    t_vals = np.linspace(0, 1.0/3.0, grid_size)
    
    min_ratio = 999.0
    min_s, min_t = -1, -1
    
    # To speed up, we can use 10 restarts per point
    for s in s_vals:
        for t in t_vals:
            if 4*s + 3*t > 1.0 + 1e-9:
                continue
            best_val, _ = get_F1_max(s, t, num_restarts=10)
            ratio = best_val / (1.5 - s - t)
            if ratio < min_ratio:
                min_ratio = ratio
                min_s = s
                min_t = t
                
    print(f"Grid search minimum ratio: {min_ratio:.6f} at s={min_s:.4f}, t={min_t:.4f}")
    
    # 2. Optimize the 14-vertex tree for p=2
    print("\n--- 2. Optimizing 14-vertex tree for p=2 ---")
    t0 = time.time()
    
    def objective_tree(params):
        gamma = params[:2]
        beta = params[2:]
        return -run_qaoa_on_subgraph(edges_tree14, (1, 2), n_tree14, gamma, beta)
        
    bounds_tree = [(0, 2*np.pi)] * 2 + [(0, np.pi)] * 2
    best_val_tree = -1
    best_params_tree = None
    
    # 15 random restarts for p=2 tree (14 qubits)
    for i in range(15):
        init_params = np.concatenate([
            np.random.uniform(0, 2*np.pi, 2),
            np.random.uniform(0, np.pi, 2)
        ])
        res = minimize(objective_tree, init_params, bounds=bounds_tree, method='L-BFGS-B')
        val = -res.fun
        if val > best_val_tree:
            best_val_tree = val
            best_params_tree = res.x
            
    t1 = time.time()
    print(f"p=2 Tree Max Expectation = {best_val_tree:.6f} (Expected 0.7559)")
    print(f"  Optimal angles: gamma = {best_params_tree[:2]}, beta = {best_params_tree[2:]}")
    print(f"  Optimization took {t1-t0:.3f} seconds")
    print("="*60)
    
    return {
        "min_ratio": min_ratio,
        "min_s": min_s,
        "min_t": min_t,
        "tree_p2_val": best_val_tree
    }

if __name__ == "__main__":
    run_reproduction()
