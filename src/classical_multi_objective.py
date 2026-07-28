import os
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

def generate_conflicting_graph(n=10, edge_prob=0.4, seed=42):
    """
    Generates a random graph where each edge has two conflicting weights (Cost vs. Latency).
    """
    np.random.seed(seed)
    G = nx.erdos_renyi_graph(n=n, p=edge_prob, seed=seed)
    
    # Assign weights
    for u, v in G.edges():
        # Objective 1: "Cost" (uniformly distributed)
        w1 = np.random.uniform(0.1, 1.0)
        # Objective 2: "Latency" (negatively correlated with Cost to create conflict)
        w2 = 1.1 - w1 + np.random.normal(0, 0.05)
        w2 = np.clip(w2, 0.05, 1.0)
        
        G[u][v]['weight_cost'] = w1
        G[u][v]['weight_latency'] = w2
        
    return G

def brute_force_cuts(G, n):
    """
    Brute-forces all 2**(n-1) unique cuts to calculate both objectives.
    Returns a list of tuples: (cost_value, latency_value, bitstring)
    """
    all_cuts = []
    edges = list(G.edges(data=True))
    
    # We only need to check the first half of the states to avoid symmetry
    num_unique_states = 2**(n - 1)
    
    for state_idx in range(num_unique_states):
        # Convert state index to a binary array of length n
        z = np.array([(state_idx >> i) & 1 for i in range(n)])
        
        cost_val = 0.0
        latency_val = 0.0
        
        for u, v, data in edges:
            if z[u] != z[v]:
                cost_val += data['weight_cost']
                latency_val += data['weight_latency']
                
        all_cuts.append((cost_val, latency_val, state_idx))
        
    return all_cuts

def find_pareto_front(all_cuts):
    """
    Filters out dominated cuts to identify the True Pareto Front.
    A point A dominates B if A is at least as good as B in all objectives, and strictly better in at least one.
    """
    pareto_points = []
    for i, p1 in enumerate(all_cuts):
        dominated = False
        for j, p2 in enumerate(all_cuts):
            if i == j:
                continue
            # p2 dominates p1 if both objectives are >= and at least one is >
            if (p2[0] >= p1[0] and p2[1] >= p1[1] and 
                (p2[0] > p1[0] or p2[1] > p1[1])):
                dominated = True
                break
        if not dominated:
            pareto_points.append(p1)
            
    # Sort Pareto points by the first objective (Cost) for plotting
    pareto_points.sort(key=lambda x: x[0])
    return pareto_points

def solve_weighted_sum(all_cuts, lambdas):
    """
    Solves the single-objective weighted sum: max (lambda * Cost + (1 - lambda) * Latency)
    for each lambda in lambdas.
    Returns a list of discovered cuts.
    """
    wsm_results = []
    for lmb in lambdas:
        best_val = -1e9
        best_cut = None
        for cut in all_cuts:
            val = lmb * cut[0] + (1.0 - lmb) * cut[1]
            if val > best_val:
                best_val = val
                best_cut = cut
        wsm_results.append(best_cut)
        
    # Remove duplicate cuts from WSM results
    unique_wsm = list(set(wsm_results))
    unique_wsm.sort(key=lambda x: x[0])
    return unique_wsm

def run_classical_reproduction():
    n = 10
    print("="*60)
    print("RUNNING MULTI-OBJECTIVE CLASSICAL WRAPPER")
    print("="*60)
    
    # 1. Generate Graph
    print("Generating conflicting graph (10 vertices)...")
    G = generate_conflicting_graph(n=n)
    print(f"Graph generated with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    
    # 2. Brute Force
    print("Brute-forcing all 512 unique cuts...")
    all_cuts = brute_force_cuts(G, n)
    
    # 3. Find True Pareto Front
    print("Sorting cuts to identify True Pareto Front...")
    pareto_front = find_pareto_front(all_cuts)
    print(f"Found {len(pareto_front)} Pareto optimal cuts.")
    
    # 4. Run WSM
    print("Running Weighted Sum Method (WSM) for 101 lambdas in [0, 1]...")
    lambdas = np.linspace(0, 1, 101)
    wsm_discovered = solve_weighted_sum(all_cuts, lambdas)
    print(f"WSM discovered {len(wsm_discovered)} unique cuts.")
    
    # Check if WSM missed any Pareto points
    wsm_ids = {cut[2] for cut in wsm_discovered}
    missed_points = [p for p in pareto_front if p[2] not in wsm_ids]
    print(f"Number of Pareto optimal points missed by WSM: {len(missed_points)}")
    
    # 5. Plotting
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plots_dir = os.path.join(project_root, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    plt.figure(figsize=(10, 7))
    
    # Plot all cuts
    costs = [c[0] for c in all_cuts]
    latencies = [c[1] for c in all_cuts]
    plt.scatter(costs, latencies, color='#d3d3d3', alpha=0.6, label='All Cuts ($2^{n-1}$ unique)')
    
    # Plot True Pareto Front
    pareto_costs = [p[0] for p in pareto_front]
    pareto_latencies = [p[1] for p in pareto_front]
    plt.plot(pareto_costs, pareto_latencies, 'o-', color='#e74c3c', linewidth=2.5, markersize=8, label='True Pareto Front')
    
    # Plot WSM Discovered
    wsm_costs = [w[0] for w in wsm_discovered]
    wsm_latencies = [w[1] for w in wsm_discovered]
    plt.scatter(wsm_costs, wsm_latencies, color='#2ecc71', marker='*', s=150, zorder=5, label='WSM Discovered')
    
    # Highlight missed points if any
    if missed_points:
        missed_costs = [m[0] for m in missed_points]
        missed_latencies = [m[1] for m in missed_points]
        plt.scatter(missed_costs, missed_latencies, color='#f1c40f', marker='x', s=100, zorder=6, label='Missed by WSM (Non-convex)')
        
    plt.title('Multi-Objective MaxCut: True Pareto Front vs. WSM Discovered', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Objective 1: Cost Cut Value', fontsize=12)
    plt.ylabel('Objective 2: Latency Cut Value', fontsize=12)
    plt.legend(loc='lower left', frameon=True)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    # Save plots
    save_path = os.path.join(plots_dir, 'multi_objective_pareto.png')
    plt.savefig(save_path, dpi=200)
    
    # Also save to Antigravity brain/artifact directory if it exists
    artifact_dir = r"C:\Users\pravi\.gemini\antigravity\brain\ab65431b-b202-4229-aaab-b1d80659ce68"
    if os.path.exists(artifact_dir):
        plt.savefig(os.path.join(artifact_dir, 'multi_objective_pareto.png'), dpi=200)
        
    plt.close()
    print(f"Saved plot to {save_path}")
    print("="*60)

if __name__ == "__main__":
    run_classical_reproduction()
