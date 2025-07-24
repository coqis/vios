---
comments: true
---

# QuarkStudio

<!-- ## **About QOS**
A **Quantum Operating System(QOS)** is an advanced software framework designed to control and manage quantum computing hardware. Unlike traditional operating systems that govern classical computers, quantum operating systems are tailored specifically for the unique requirements of quantum computing architectures.

At its core, a quantum operating system provides the necessary abstraction layer between the user or programmer and the underlying quantum hardware. This abstraction allows researchers, engineers, and developers to interact with quantum computers without needing to have an in-depth understanding of the complex physics governing quantum systems.
???- abstract "Key components of a QOS"
    Key components of a quantum operating system include:

    1. **Quantum Programming Interface**: A quantum operating system offers high-level programming interfaces that enable users to write quantum algorithms in familiar programming languages or quantum-specific languages such as Qiskit, Cirq, or Quipper. These interfaces abstract the complexities of quantum mechanics, allowing programmers to focus on algorithm design rather than hardware details.

    2. **Resource Management**: Quantum computers have limited qubit and gate resources, and managing these resources efficiently is crucial for running complex quantum algorithms. The operating system handles resource allocation, scheduling, and optimization to maximize the utilization of available quantum hardware while minimizing errors and overhead.

    3. **Hardware Abstraction Layer**: Quantum computers consist of diverse architectures, including superconducting qubits, trapped ions, and photonic systems. The operating system provides a unified interface that abstracts the underlying hardware differences, allowing users to write code that is portable across different quantum platforms.

    4. **Integration with Classical Computing Resources**: Quantum algorithms often require classical pre- and post-processing steps, such as data input/output, classical control, and result analysis. The operating system seamlessly integrates quantum and classical computing resources, facilitating the execution of hybrid quantum-classical algorithms.

    ***Overall, a quantum operating system plays a crucial role in advancing the field of quantum computing by providing a scalable, efficient, and user-friendly platform for developing and executing quantum algorithms. As quantum hardware continues to evolve, the role of quantum operating systems will become increasingly important in realizing the full potential of quantum technologies.*** -->



## **Introduction**

A **Quantum Operating System(QOS)** is an advanced software framework designed to control and manage quantum computing hardware. Unlike traditional operating systems that govern classical computers, quantum operating systems are tailored specifically for the unique requirements of quantum computing architectures.

<!-- `quarkstudio` mainly focus on the second, third, and fourth points as described in [Introduction to QOS](#about-qos). -->
[***QuarkStudio***](quark) is designed as a QOS and developed by the [Superconducting Quantum Computing Group](http://sqc.baqis.ac.cn/) from [Beijing Academy of Quantum Information Sciences](http://baqis.ac.cn/).



## **Installation**


<!-- ### **About SystemQ**
[**SystemQ**](https://gitee.com/baqis/systemq.git) is designed as a QOS and developed by the [Superconducting Quantum Computing Group](http://sqc.baqis.ac.cn/) from [Beijing Academy of Quantum Information Sciences](http://baqis.ac.cn/). SystemQ mainly consists of three subsystems, namely **systemq**, **waveforms** and **quarkstudio**.

- [`systemq`](https://gitee.com/baqis/systemq.git) is primarily targeted towards end users, offering a range of pre-written functional modules while also enabling users to customize any desired functionalities.
- [`waveforms`](../waveform/) mainly focus on the first point described in [Introduction to QOS](../#introduction-to-qos).
- [`quarkstudio`](../quark/) mainly focus on the second, third, and fourth points described in [Introduction to QOS](../#introduction-to-qos) -->


<!-- ### **How to start** -->
<!-- For instructions on how to use SystemQ, please refer to [Usage](https://quarkstudio.readthedocs.io/en/latest/usage/) -->

The following requirements ***MUST*** be met before starting to use:
<div class="result" markdown>
???+ warning "Requirements"
    <!-- ![SystemQ](image/aniatom.gif){ align=right width="150"} -->

    |name|version|check|
    |---|---|---|
    |:material-git: [git](https://git-scm.com/)|~|`git -v`|
    |:material-language-python: [python](https://python.org)|3.12|`python -V`|
</div>

<!-- First, download [**SystemQ**](https://gitee.com/baqis/systemq.git), and it is highly recommended to use :material-git:[git](https://git-scm.com/).  -->
Then you can install `quarkstudio` and start using from the beginner's [**tutorial**](tutorial.md).
???+ note "Installation"
    ``` bash
    # install quarkstudio
    pip install -U quarkstudio

    # download drivers/libraries to `~/Desktop/home` and install the requirements
    quark init --home ~/Desktop/home
    ```

???+ warning "command not found"
    **If you encounter errors like "command not found" or similar, make sure the git or Python Scripts directory is added to the environment variable!**
    <!-- **Make sure that systemq has been installed succesfully(run `pip show systemq` to check)** -->


:material-email: Contact [fengyl@baqis.ac.cn]()

