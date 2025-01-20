import networkx as nx
import json
from .quantumcircuit import QuantumCircuit
from .quantumcircuit_helpers import one_qubit_gates_available,one_qubit_parameter_gates_available
from .transpiler import Transpiler
from .backend import Backend
from .dag import qc2dag
from pathlib import Path

def call_quark_transpiler(qc:QuantumCircuit|list|str,chip_name:str,compile:bool, options:dict,dev=False,return_qlisp=True):
    if chip_name != 'Baihua':
        chip_name += '1'

    if dev:
        with open(Path.home()/f'Desktop/home/test/{chip_name}1.json') as f:
            chip_info =  json.loads(f.read())
        chip_backend = Backend(chip_info)
        chip_backend.chip_name = chip_name
    else:
        chip_backend = Backend(chip_name)

    # 初始化线路,检查线路中的门是否都支持。
    if isinstance(qc, QuantumCircuit):
        quarkQC = qc
    elif isinstance(qc, str):
        quarkQC = QuantumCircuit().from_openqasm2(qc)
    elif isinstance(qc, list):
        quarkQC = QuantumCircuit().from_qlisp(qc)
    else:
        raise(TypeError(f'The qc format is incorrect, only str, list and QuantumCircuit are supported. The format you provided is {type(qc)}.'))
    
    # check measure 是否存在，且位于线路末尾
    dag = qc2dag(quarkQC)
    n_measure = 0
    insert_barrier = False
    for node in dag.nodes():
        if 'measure' in node:
            n_measure += 1
            if dag.out_degree(node) > 0:
                raise(ValueError(f'There are gate {gate_info[0]} after the measurement gate.'))
            for predecessor in dag.predecessors(node):
                if 'barrier' not in predecessor:
                    insert_barrier = True
    # 如果 measure 不存在，add barrier, add measure
    if n_measure == 0:
        print('There is no measurement gate in the circuit, quarkcircuit will add measure for all qubits.')
        quarkQC.barrier()
        quarkQC.ncbits = len(quarkQC.qubits)
        quarkQC.measure(quarkQC.qubits,[i for i in range(quarkQC.ncbits)])
    # 如果 measure存在 但没有隔离则添加隔离
    if n_measure > 0 and insert_barrier:
        new = []
        measure_gates = []
        barrier_gates = [('barrier',tuple(quarkQC.qubits))]
        for gate_info in quarkQC.gates:
            gate = gate_info[0]
            if gate == 'measure':
                measure_gates.append(gate_info)
            else:
                new.append(gate_info)
        quarkQC.gates = new + barrier_gates + measure_gates

    # delay duration
    for gate_info in quarkQC.gates:
        if gate_info[0] == 'delay':
            duration = gate_info[1] #quarkcircuit unit is ns
            if duration*1e-9 > 100e-6:
                raise(ValueError(f'The maximum delay is 100us, you provided is {duration} ns.'))
            
    # compile
    if compile:
        set_use_priority = options.get('use_priority',True)
        set_initial_mapping = options.get('initial_mapping',{'key':'fidelity_var','topology':'linear1'})
        set_optimize_level = options.get('optimize_level',1)
        quarkQC_compiled = Transpiler(quarkQC,chip_backend).run(
            use_priority = set_use_priority,
            initial_mapping = set_initial_mapping,
            optimize_level = set_optimize_level,
            )
    else:
        gates_availale = list(one_qubit_gates_available.keys()) \
            + list(one_qubit_parameter_gates_available.keys()) \
            + ['cx','cz','barrier','measure'] #chip 支持的语法
        collect_two_qubit_gates = []
        for gate_info in quarkQC.gates:
            gate = gate_info[0]
            if gate not in gates_availale:
                raise(ValueError(f'The {gate} gate you provided is not supported by the current chip. Please convert to basis gates.'))
            if gate in ['cx','cz']:
                collect_two_qubit_gates.append(gate_info)

        # check qubits existance and fidelity 
        subgraph = chip_backend.graph.subgraph(quarkQC.qubits)
        for node in quarkQC.qubits:
            if subgraph.has_node(node):
                fidelity = nx.get_node_attributes(subgraph,'fidelity')[node]
                if fidelity == 0.:
                    raise(ValueError(f'The physical qubit {node} selected by the user is died.')) 
            else:
                raise(KeyError(f'Physical qubit {node} does not exit.'))
        # check edge fidelity and connectivity
        
        is_connected = nx.is_connected(subgraph)
        for _, fidelity in nx.get_edge_attributes(subgraph,'fidelity').items():
            if fidelity == 0.:
                is_connected = False
            if is_connected is False:
                raise(ValueError(f'The physical qubit layout {quarkQC.qubits} selected by the user is not connected.'))  
            
        for two_qubit_gates_info in collect_two_qubit_gates:
            gate,qubit1,qubit2 = two_qubit_gates_info
            if subgraph.has_edge(qubit1, qubit2):
                continue
            else:
                raise(ValueError(f'The {two_qubit_gates_info} cannot be executed directly by the chip. Please insert SWAP gates or reselect the layout.'))

        quarkQC_compiled = quarkQC

    # check CZ
    if quarkQC_compiled.ncz > 100:
        raise(ValueError(f'The number of two-qubit gates in the circuit is {ncz} exceeds 100.'))
    
    if return_qlisp:
        qlisp = quarkQC_compiled.to_qlisp
        return qlisp
    else:
        return quarkQC_compiled

if __name__ == '__main__':
    nqubits = 4
    qc = QuantumCircuit(nqubits)
    for i in range(1,nqubits):
        qc.cx(0,i)
    qc.barrier()
    qc.measure_all()
    qct_qlisp = call_quark_transpiler(qc,'Dongling1','True',{})
    print(qct_qlisp)