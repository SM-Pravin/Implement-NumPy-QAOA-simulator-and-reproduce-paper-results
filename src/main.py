import os
import numpy as np
import matplotlib.pyplot as plt
import time

from ring_reproduction import optimize_ring_p
from three_regular_reproduction import get_F1_max, edges_tree14, n_tree14, run_qaoa_on_subgraph
from scipy.optimize import minimize

# Set up matplotlib style for professional scientific plots
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.5
plt.rcParams['grid.linestyle'] = '--'

def generate_ring_plots(ring_results, save_dirs):
    print("Generating Ring of Disagrees plots...")
    p_vals = list(ring_results.keys())
    numerical_ratios = [ring_results[p][0] for p in p_vals]
    theoretical_ratios = [ring_results[p][1] for p in p_vals]
    
    plt.figure()
    plt.plot(p_vals, theoretical_ratios, 'o-', color='#1f77b4', linewidth=2.5, markersize=8, label='Theoretical: $(2p+1)/(2p+2)$')
    plt.plot(p_vals, numerical_ratios, 'x--', color='#ff7f0e', linewidth=1.5, markersize=10, label='Reproduction (Numerical Max)')
    
    plt.title('QAOA on the Ring of Disagrees (MaxCut)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('QAOA depth $p$', fontsize=12)
    plt.ylabel('Approximation Ratio ($M_p / n$)', fontsize=12)
    plt.xticks(p_vals)
    plt.ylim(0.70, 0.95)
    plt.legend(loc='lower right', frameon=True, facecolor='white', edgecolor='none')
    plt.tight_layout()
    
    for save_dir in save_dirs:
        save_path = os.path.join(save_dir, 'ring_disagrees.png')
        plt.savefig(save_path, dpi=200)
        print(f"Saved plot to {save_path}")
    plt.close()

def generate_three_regular_landscape(save_dirs):
    print("Generating 3-regular graph s-t approximation ratio landscape...")
    # Generate a grid of s and t values
    grid_res = 30
    s_vals = np.linspace(0, 0.25, grid_res)
    t_vals = np.linspace(0, 1.0/3.0, grid_res)
    
    S, T = np.meshgrid(s_vals, t_vals)
    R = np.zeros_like(S)
    
    # We will evaluate F1_max at each valid grid point
    # To make this fast, we can use a smaller number of restarts (e.g. 8)
    for i in range(grid_res):
        for j in range(grid_res):
            s = S[i, j]
            t = T[i, j]
            if 4*s + 3*t > 1.0 + 1e-9:
                R[i, j] = np.nan
            else:
                best_val, _ = get_F1_max(s, t, num_restarts=8)
                R[i, j] = best_val / (1.5 - s - t)
                
    plt.figure(figsize=(9, 7))
    
    # Create contour plot
    contour = plt.contourf(S, T, R, levels=20, cmap='viridis')
    cbar = plt.colorbar(contour)
    cbar.set_label('Approximation Ratio', rotation=270, labelpad=15)
    
    # Draw boundary 4s + 3t = 1
    s_boundary = np.linspace(0, 0.25, 100)
    t_boundary = (1.0 - 4*s_boundary) / 3.0
    plt.plot(s_boundary, t_boundary, 'r--', linewidth=2, label='Domain Boundary: $4s + 3t = 1$')
    
    # Mark the minimum ratio point (0, 0)
    plt.plot(0, 0, '*', color='red', markersize=15, label='Worst Case Minimum: 0.6924')
    plt.annotate('Worst Case (0.6924)\nat $s=0, t=0$', xy=(0.005, 0.005), xytext=(0.04, 0.05),
                 arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=8),
                 fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.3))
                 
    plt.title('QAOA $p=1$ Approximation Ratio on 3-Regular Graphs', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Crossed Squares fraction $s = S/n$', fontsize=12)
    plt.ylabel('Isolated Triangles fraction $t = T/n$', fontsize=12)
    plt.xlim(-0.01, 0.26)
    plt.ylim(-0.01, 0.35)
    plt.legend(loc='upper right')
    plt.tight_layout()
    
    for save_dir in save_dirs:
        save_path = os.path.join(save_dir, 'three_regular_landscape.png')
        plt.savefig(save_path, dpi=200)
        print(f"Saved plot to {save_path}")
    plt.close()

def main():
    # Find project root and prepare plots directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_plots_dir = os.path.join(project_root, 'plots')
    os.makedirs(workspace_plots_dir, exist_ok=True)
    
    # Antigravity brain/artifact directory
    artifact_dir = r"C:\Users\pravi\.gemini\antigravity\brain\ab65431b-b202-4229-aaab-b1d80659ce68"
    
    save_dirs = [workspace_plots_dir]
    if os.path.exists(artifact_dir):
        save_dirs.append(artifact_dir)
        
    print("="*60)
    print("MASTER QAOA REPRODUCTION WORKFLOW")
    print("="*60)
    
    # 1. Run Ring reproduction
    ring_results = {}
    print("\n--- Running Ring of Disagrees Optimization ---")
    prev_params = None
    for p in range(1, 7):
        t0 = time.time()
        num_restarts = 12 if p <= 3 else (3 if p <= 5 else 1)
        best_val, best_params = optimize_ring_p(p, prev_params, num_random_restarts=num_restarts)
        t1 = time.time()
        theoretical = (2 * p + 1) / (2 * p + 2)
        print(f"p={p}: Numerical={best_val:.12f}, Theoretical={theoretical:.12f}, Time={t1-t0:.2f}s")
        ring_results[p] = (best_val, theoretical, best_params)
        prev_params = best_params
        
    # Generate Ring plots
    generate_ring_plots(ring_results, save_dirs)
    
    # 2. Run 3-regular graph reproduction
    print("\n--- Running 3-Regular Graph Optimizations ---")
    # Verify the p=2 tree expectation value
    print("Optimizing 14-vertex tree for p=2...")
    t0 = time.time()
    def objective_tree(params):
        gamma = params[:2]
        beta = params[2:]
        return -run_qaoa_on_subgraph(edges_tree14, (1, 2), n_tree14, gamma, beta)
    
    bounds_tree = [(0, 2*np.pi)] * 2 + [(0, np.pi)] * 2
    best_val_tree = -1
    for _ in range(15):
        init_params = np.concatenate([
            np.random.uniform(0, 2*np.pi, 2),
            np.random.uniform(0, np.pi, 2)
        ])
        res = minimize(objective_tree, init_params, bounds_tree, method='L-BFGS-B')
        val = -res.fun
        if val > best_val_tree:
            best_val_tree = val
            
    t1 = time.time()
    print(f"p=2 Tree Expectation: Numerical={best_val_tree:.6f} (Expected 0.755906), Time={t1-t0:.2f}s")
    
    # Generate 3-regular graph landscape plot
    generate_three_regular_landscape(save_dirs)
    
    print("\nMaster Workflow Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
