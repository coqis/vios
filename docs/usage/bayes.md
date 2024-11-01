# Bayesian Correction of Measure Results(by Pei Liu)

The Bayes rule,
$P(A_i|B)=\frac{P(B|A_i)P(A_i)}{\sum_j P(B|A_j)P(A_j)}$
is the basis for the following discussion to reduce the classic errors in measurements.

## The simple case for one qubit

For one qubit,
it is obvious that
$\begin{aligned}
\begin{pmatrix}P(\text{measure }|0\rangle)\\P(\text{measure }|1\rangle)\end{pmatrix}&=
\begin{pmatrix}
P(\text{measure }|0\rangle|\text{prepare }|0\rangle)&
P(\text{measure }|0\rangle|\text{prepare }|1\rangle)\\
P(\text{measure }|1\rangle|\text{prepare }|0\rangle)&
P(\text{measure }|1\rangle|\text{prepare }|1\rangle)
\end{pmatrix}
\begin{pmatrix}P(\text{prepare }|0\rangle)\\P(\text{prepare }|1\rangle)\end{pmatrix}\\
&={M}\begin{pmatrix}P(\text{prepare }|0\rangle)\\P(\text{prepare }|1\rangle)\end{pmatrix}.
\end{aligned}$
The elements of $M$ can be extracted from prior expriments,
such as
1. The qubit is prepared in the ground state and then measured with the probability $P(\text{measure }|0\rangle|\text{prepare }|0\rangle)$ in the ground state the $P(\text{measure }|1\rangle|\text{prepare }|0\rangle)$ in the first excited state.
2. Then the qubit is prepared in the first excited state and measured with the probability $P(\text{measure }|0\rangle|\text{prepare }|1\rangle)$ in the ground state the $P(\text{measure }|1\rangle|\text{prepare }|1\rangle)$ in the first excited state.

With the correction matrix $M^{-1}$,
results from any other circuit can be processed by
${M}^{-1}\begin{pmatrix}P(\text{measure }|0\rangle)\\P(\text{measure }|1\rangle)\end{pmatrix}=\begin{pmatrix}P(\text{prepare }|0\rangle)\\P(\text{prepare }|1\rangle)\end{pmatrix}
=\begin{pmatrix}
P(\text{the ideal measurement result will be }|0\rangle)\\
P(\text{the ideal measurement result will be }|1\rangle)\end{pmatrix}.$
Attention to that the errors in preparation is ignored.

## Naive case for more qubits
For $N$ qubits,
the basis state can be expressed by
$|k\rangle\equiv|a_0\rangle\otimes|a_1\rangle\otimes\cdots\otimes|a_{N-1}\rangle$
with $(a_0a_1\cdots a_{N-1})_2$ is the binary representation of $k$,
i.e.
$k=\sum_{j=0}^{N-1}a_j\cdot2^{N-1-j}=(a_0a_1\cdots a_{N-1})_2$

Thereore,
$\begin{aligned}
P(\text{the ideal measurement result will be }|k\rangle)
&=\sum_{l=0}^{2^N-1}P(\text{prepare }|k\rangle|\text{measure }|l\rangle)P(\text{measure }|l\rangle)\\
&=\sum_{l=0}^{2^N-1}(M^{-1})_{k, l}P(\text{measure }|l\rangle.
\end{aligned}$

The elements of correction matrix $M^{-1}$ can also be extracted from prior expriments,
and the step to determine $P(\text{measure }|k\rangle|\text{prepare }|l\rangle)$ is similar to the one qubit case.

However,
the complexity to obtain readout correction matrix and the dimension of readout correction matrix grow exponentially as the qubit number $N$ increases,
so that the naive method is almost impossible accomplished when $N\sim20$.

## Correction under some approximations

With some assumptions, 
the calculation process will be simplified.
For example,
two assumptions are considered in the following instance.

1. The measurement correlations between diffirent qubits are ignored,
i.e.
$P(\text{prepare }|k\rangle|\text{measure }|l\rangle)=\prod_{j=0}^{N-1}P(\text{prepare }|a_j\cdot2^{N-1-j}\rangle|\text{measure }|b_j\cdot2^{N-1-j}\rangle)$
with $k=(a_0a_1\cdots a_{N-1})_2$ and $l=(b_0b_1\cdots b_{N-1})_2$.

2. Only some states with high probability appearing in the ideal measurement results are considered.

Another fact is that the readout error is relative small in a well-calibrated system,
i.e. $P(\text{measure }|k\rangle|\text{prepare }|k\rangle)\gg P(\text{measure }|l\rangle|\text{prepare }|k\rangle), l\neq k$.

For a state $|l\rangle$ with the probability $P(\text{measure }|l\rangle)$ in the original measurement result,
it generally contributes to all of the $2^N$ states.
But from the first assumption,
the magnitude of the influence can be sorted within the complexity $\mathcal O(N\log N)$ and it decreases rapidly. If the influences are considered in the decreasing order and the current one is small enough, all of remains which are no larger than the current one can be dropped. The second assumption restricts the size of the state to be considered and what is small enough.
If the number of considered set is $S$,
the complexity is about $\mathcal O(S\log S)$ with proper data structure.
Because a total of $R$ shots are applied,
the complexity can be roughly estimated as $\mathcal O(RN\log N+RS\log S)\approx\mathcal O(RS\log S)$.

It's worth noting that some tiny value are dropped and actually this algorithm is an approximation algorithm.
Meanwhile the considering order of diffirent shots has an effect on the efficiency.

In python such process can be quick calculated by `waveforms.math.bayes.bayesian_correction`,
based on the Fibonacci heap.
```python
'''
bayesian_correction(state, correction_matrices, *, subspace=None, size_lim=1024, eps=1e-06)
    Apply a correction matrix to a state.
    
    Args:
        state (np.array, dtype=int): The state to be corrected.
        correction_matrices (np.array): A list of correction matrices.
        subspace (np.array, dtype=int): The basis of subspace.
        size_lim (int): The maximum size of the heap, relative to the number of consider states.
        eps (float): The minimum probability of the state.
    
    Returns:
        np.array: The corrected state or counts.
'''
```

```python

state = np.random.randint(2, size = (101, 1024, 4))
# generate a random result for test, the last dimension is the number of measured qubits, the penultimate dimension is the number of shots
# only the last two dimensions are important


PgPe = np.array([[0.1, 0.8], [0.03, 0.91], [0.02, 0.87], [0.05, 0.9]])
correction_matrices = np.array([np.array([[Pe, Pe - 1], [-Pg, 1 - Pg]]) / (Pe - Pg) for Pg, Pe in PgPe]) 
# generate correction matrices for the four qubits respectively

from waveforms.math.bayes import bayesian_correction
result = bayesian_correction(state, correction_matrices, size_lim=2000, eps=1e-5)
# calculate the correction reuslt
```


The `result` in this case returns with a shape
```python
(101, )
```
and each `result[0]` seems like
```python
{(0, 1, 0, 1): 0.04855336613672877,
 (1, 1, 1, 0): 0.050944311757122586,
 (1, 0, 0, 1): 0.05551078260515436,
 (1, 1, 0, 0): 0.05648806261725934,
 (0, 0, 1, 0): 0.05947065072686814,
 (1, 0, 1, 0): 0.06225579793665462,
 (0, 1, 0, 0): 0.06450492191361831,
 (0, 0, 0, 0): 0.06547133830972232,
 (0, 0, 0, 1): 0.06707908106842332,
 (0, 0, 1, 1): 0.06758531109218416,
 (1, 0, 0, 0): 0.07055826435269971,
 (1, 0, 1, 1): 0.07181082325978526,
 (0, 1, 1, 1): 0.07278652123449646,
 (1, 1, 1, 1): 0.07561217606193549,
 (1, 1, 0, 1): 0.08241680853073179,
 (0, 1, 1, 0): 0.09344204468217768}
```

The `waveforms` can be installed by `pip` or other common install methods,
```
pip install -U waveforms
```

 









