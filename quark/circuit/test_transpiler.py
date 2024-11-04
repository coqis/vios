from typing import Literal
from quark.circuit import QuantumCircuit, generate_ghz_state, Transpiler, Backend

def call_quarkcircuit_transpiler(
        qc: QuantumCircuit | str | list,
        chip_name: Literal['Baihua'] = 'Baihua',
        use_priority: bool = True,
        initial_mapping: list | None = None,
        optimize_level = 0,
        ):
    
    # qc， compile, backend, level, 
    chip_backend = Backend(chip_name)
    qct = Transpiler(qc,chip_backend=chip_backend).run(use_priority=use_priority,
                                                      initial_mapping=initial_mapping,
                                                      optimize_level=optimize_level)

    return qct.to_qlisp


if __name__ == '__main__':
    nqubits = 4
    qc = generate_ghz_state(nqubits)
    qct_qlisp = call_quarkcircuit_transpiler(qc)
    print(qct_qlisp)