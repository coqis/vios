---
icon: simple/manageiq
---


# Introduction

`QuarkStudio` mainly includes the following components:

???+ abstract "QuarkStudio"

    1. [**QuarkServer**](server.md): QuarkServer is responsible for task scheduling, hardware management, instruction execution, and data storage. 

        1. **Task Scheduling**: This feature is suitable for scenarios like user experiments or quantum applications, allowing for the pipeline scheduling of multiple tasks using different strategies.

        2. **Hardware Management**: Abstracting a unified hardware interface, hardware functionalities are implemented by hardware manufacturers. This isolation between users and hardware ensures that users don't need to concern themselves with the actual hardware details, but rather focus on the logic of their experiments.

        3. **Instruction Execution**: This is the core functionality of QuarkServer. Utilizing instruction pipelines and leveraging the multi-core advantages of computers, tasks are executed in a highly parallelized manner, minimizing the time delay between tasks and instructions.

        4. **Data Storage**: Data is automatically stored upon task completion and provides interfaces for users to trace historical data.

    2. [**QuarkStudio**](studio.md): QuarkStudio provides users with a user-friendly visual interface for more direct interaction with QuarkServer. It includes features such as data visualization, parameter querying and modification, and data retrieval.
    3. [**QuarkCanvas**](canvas.md): QuarkCanvas is primarily used for real-time display of waveforms sent to the device like an **oscilloscope**.
    4. [**QuarkViewer**](viewer.md): QuarkViewer is primarily used for real-time data visualization.
    5. [**QuarkRemote**](remote.md): QuarkRemote virtualizes devices with built-in operating systems (typically Windows or Linux) as a service and connects them to the local host via RPC (Remote Procedure Call), allowing for seamless communication with the devices through a unified interface. It also implements advanced functionalities such as remote software updates for devices and retrieving device status information.