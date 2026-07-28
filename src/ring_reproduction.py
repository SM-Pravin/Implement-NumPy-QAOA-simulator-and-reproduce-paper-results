import numpy as np
import time
from scipy.optimize import minimize
from qaoa_simulator import run_qaoa_on_subgraph

def optimize_ring_p(p, prev_best_params=None, num_random_restarts=15):
    """
    Optimizes the QAOA angles for the Ring of Disagrees at level p.
    If prev_best_params is provided, it uses it for warm starts.
    """
    n = 2 * p + 2
    edges_G = [(i, i+1) for i in range(2 * p + 1)]
    target_edge = (p, p + 1)
    
    def objective(params):
        gamma = params[:p]
        beta = params[p:]
        # We want to maximize the expectation, so minimize negative
        return -run_qaoa_on_subgraph(edges_G, target_edge, n, gamma, beta)
    
    bounds = [(0, 2 * np.pi)] * p + [(0, np.pi)] * p
    
    best_val = -1
    best_params = None
    
    # Compile list of initial guesses
    initial_guesses = []
    
    # 1. Warm starts if previous results are available
    if prev_best_params is not None:
        p_prev = len(prev_best_params) // 2
        gamma_prev = prev_best_params[:p_prev]
        beta_prev = prev_best_params[p_prev:]
        
        # Heuristic A: append 0
        guess_a = np.concatenate([gamma_prev, [0.1], beta_prev, [0.1]])
        initial_guesses.append(guess_a)
        
        # Heuristic B: prepend 0
        guess_b = np.concatenate([[0.1], gamma_prev, [0.1], beta_prev])
        initial_guesses.append(guess_b)
        
        # Heuristic C: linear interpolation (standard QAOA parameter path)
        t_prev = np.linspace(0, 1, p_prev)
        t_curr = np.linspace(0, 1, p)
        gamma_curr = np.interp(t_curr, t_prev, gamma_prev)
        beta_curr = np.interp(t_curr, t_prev, beta_prev)
        initial_guesses.append(np.concatenate([gamma_curr, beta_curr]))
        
        # Heuristic D: perturbation of linear interpolation
        for _ in range(3):
            noise = np.random.normal(0, 0.1, 2 * p)
            guess_d = np.clip(np.concatenate([gamma_curr, beta_curr]) + noise, 0, np.pi)
            initial_guesses.append(guess_d)
            
    # 2. Random restarts
    for _ in range(num_random_restarts):
        init_gamma = np.random.uniform(0, 2 * np.pi, p)
        init_beta = np.random.uniform(0, np.pi, p)
        initial_guesses.append(np.concatenate([init_gamma, init_beta]))
        
    # Run the optimizations
    for init_params in initial_guesses:
        res = minimize(objective, init_params, bounds=bounds, method='L-BFGS-B')
        val = -res.fun
        if val > best_val:
            best_val = val
            best_params = res.x
            
    return best_val, best_params

def run_reproduction():
    print("="*60)
    print("REPRODUCING RING OF DISAGREES (SECTION IV)")
    print("="*60)
    print(f"{'p':<5}{'Numerical Max':<18}{'Theoretical':<18}{'Difference':<15}{'Time (s)':<10}")
    print("-"*66)
    
    prev_params = None
    results = {}
    
    for p in range(1, 7):
        t0 = time.time()
        # Reduce random restarts for larger p to speed up, since warm starts are very good
        num_restarts = 15 if p <= 3 else 8
        best_val, best_params = optimize_ring_p(p, prev_params, num_random_restarts=num_restarts)
        t1 = time.time()
        
        theoretical = (2 * p + 1) / (2 * p + 2)
        diff = abs(best_val - theoretical)
        
        print(f"{p:<5}{best_val:<18.12f}{theoretical:<18.12f}{diff:<15.2e}{t1-t0:<10.3f}")
        results[p] = (best_val, theoretical, best_params)
        prev_params = best_params
        
    print("="*60)
    return results

if __name__ == "__main__":
    run_reproduction()
