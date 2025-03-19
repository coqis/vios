---
comments: true
---

# Experiment

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
***QuarkStudio*** is designed as a QOS and developed by the [Superconducting Quantum Computing Group](http://sqc.baqis.ac.cn/) from [Beijing Academy of Quantum Information Sciences](http://baqis.ac.cn/).

`QuarkStudio` mainly includes the following components:

???- abstract "QuarkStudio"

    1. [**QuarkServer**](quark/server/): QuarkServer is responsible for task scheduling, hardware management, instruction execution, and data storage. 

        1. **Task Scheduling**: This feature is suitable for scenarios like user experiments or quantum applications, allowing for the pipeline scheduling of multiple tasks using different strategies.

        2. **Hardware Management**: Abstracting a unified hardware interface, hardware functionalities are implemented by hardware manufacturers. This isolation between users and hardware ensures that users don't need to concern themselves with the actual hardware details, but rather focus on the logic of their experiments.

        3. **Instruction Execution**: This is the core functionality of QuarkServer. Utilizing instruction pipelines and leveraging the multi-core advantages of computers, tasks are executed in a highly parallelized manner, minimizing the time delay between tasks and instructions.

        4. **Data Storage**: Data is automatically stored upon task completion and provides interfaces for users to trace historical data.

    2. [**QuarkStudio**](quark/studio/): QuarkStudio provides users with a user-friendly visual interface for more direct interaction with QuarkServer. It includes features such as data visualization, parameter querying and modification, and data retrieval.
    3. [**QuarkCanvas**](quark/canvas/): QuarkCanvas is primarily used for real-time display of waveforms sent to the device like an **oscilloscope**.
    4. [**QuarkRemote**](quark/remote/): QuarkRemote virtualizes devices with built-in operating systems (typically Windows or Linux) as a service and connects them to the local host via RPC (Remote Procedure Call), allowing for seamless communication with the devices through a unified interface. It also implements advanced functionalities such as remote software updates for devices and retrieving device status information.



## **Installation**


<!-- ### **About SystemQ**
[**SystemQ**](https://gitee.com/baqis/systemq.git) is designed as a QOS and developed by the [Superconducting Quantum Computing Group](http://sqc.baqis.ac.cn/) from [Beijing Academy of Quantum Information Sciences](http://baqis.ac.cn/). SystemQ mainly consists of three subsystems, namely **systemq**, **waveforms** and **quarkstudio**.

- [`systemq`](https://gitee.com/baqis/systemq.git) is primarily targeted towards end users, offering a range of pre-written functional modules while also enabling users to customize any desired functionalities.
- [`waveforms`](../waveform/) mainly focus on the first point described in [Introduction to QOS](../#introduction-to-qos).
- [`quarkstudio`](../quark/) mainly focus on the second, third, and fourth points described in [Introduction to QOS](../#introduction-to-qos) -->


<!-- ### **How to start** -->
<!-- For instructions on how to use SystemQ, please refer to [Usage](https://quarkstudio.readthedocs.io/en/latest/usage/) -->

The following requirements must be met before starting to use:
<div class="result" markdown>
???+ warning "Requirements"
    <!-- ![SystemQ](image/aniatom.gif){ align=right width="150"} -->

    |name|version|check|
    |---|---|---|
    |:material-git: [git](https://git-scm.com/)|~|`git -v`|
    |:material-language-python: [python](https://python.org)|>=3.11|`python -V`|
</div>

<!-- First, download [**SystemQ**](https://gitee.com/baqis/systemq.git), and it is highly recommended to use :material-git:[git](https://git-scm.com/).  -->
Then you can install `quarkstudio` and start using from the beginner's [**tutorial**](code/tutorial/).
???+ note "Installation"
    ``` bash
    # install quarkstudio
    pip install quarkstudio[full]

    # download drivers and libraries and initialize quark
    quark init

    # update if needed
    quark update --server
    quark update --studio
    ```

???+ warning "command not found"
    **If you encounter errors like "command not found" or similar, make sure the git or Python Scripts directory is added to the environment variable!**
    <!-- **Make sure that systemq has been installed succesfully(run `pip show systemq` to check)** -->


:material-email: Contact [fengyl@baqis.ac.cn]()

