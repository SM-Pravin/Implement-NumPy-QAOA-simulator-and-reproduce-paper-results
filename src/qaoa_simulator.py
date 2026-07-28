import numpy as np

def apply_rx(state, j, beta, n):
    """
    Applies Rx(2*beta) = exp(-i * beta * X) on qubit j of an n-qubit statevector.
    Reshapes the statevector to apply the 2x2 rotation matrix on the j-th qubit.
    """
    # Reshape to (2**(n-1-j), 2, 2**j) where axis 1 represents the j-th qubit.
    shape = (2**(n - 1 - j), 2, 2**j)
    state_reshaped = state.reshape(shape)
    
    cos_b = np.cos(beta)
    sin_b = np.sin(beta)
    
    # Rx(2*beta) = [[cos(beta), -i*sin(beta)], [-i*sin(beta), cos(beta)]]
    state_new = np.empty_like(state_reshaped)
    state_new[:, 0, :] = cos_b * state_reshaped[:, 0, :] - 1j * sin_b * state_reshaped[:, 1, :]
    state_new[:, 1, :] = -1j * sin_b * state_reshaped[:, 0, :] + cos_b * state_reshaped[:, 1, :]
    
    return state_new.reshape(-1)

def get_diagonal_operator(edges, n):
    """
    Computes the diagonal elements of the MaxCut objective function operator C
    for the given list of edges on n qubits.
    C(z) = \sum_{(u, v) \in edges} (z_u ^ z_v)
    where z_u is the u-th bit of state z.
    """
    diag = np.zeros(2**n, dtype=float)
    z = np.arange(2**n)
    for u, v in edges:
        bit_u = (z >> u) & 1
        bit_v = (z >> v) & 1
        diag += (bit_u ^ bit_v)
    return diag

def apply_phase(state, diag_C, gamma):
    """
    Applies U(C, gamma) = exp(-i * gamma * C) to the statevector.
    """
    return np.exp(-1j * gamma * diag_C) * state

def get_expectation(state, diag_D):
    """
    Computes the expectation value <psi|D|psi> of a diagonal operator D.
    """
    return np.sum(diag_D * np.abs(state)**2)

def run_qaoa_on_subgraph(edges_G, target_edge, n, gamma, beta):
    """
    Runs the QAOA circuit on an n-qubit subgraph and returns the expectation
    value of the target edge clause.
    gamma: list/array of p angles
    beta: list/array of p angles
    """
    p = len(gamma)
    # Start in uniform superposition state
    state = np.ones(2**n, dtype=complex) / np.sqrt(2**n)
    
    # Precompute diagonal of C_G
    diag_CG = get_diagonal_operator(edges_G, n)
    
    for step in range(p):
        state = apply_phase(state, diag_CG, gamma[step])
        for q in range(n):
            state = apply_rx(state, q, beta[step], n)
            
    # Target clause diagonal operator
    diag_Cjk = get_diagonal_operator([target_edge], n)
    return get_expectation(state, diag_Cjk)
