---
comments: true
---

# **Introduction to SystemQ**


### **About SystemQ**
[**SystemQ**](https://gitee.com/baqis/systemq.git) is designed as a QOS and developed by the [Superconducting Quantum Computing Group](http://sqc.baqis.ac.cn/) from [Beijing Academy of Quantum Information Sciences](http://baqis.ac.cn/). SystemQ mainly consists of three subsystems, namely **systemq**, **waveforms** and **quarkstudio**.

- [`systemq`](https://gitee.com/baqis/systemq.git) is primarily targeted towards end users, offering a range of pre-written functional modules while also enabling users to customize any desired functionalities.
- [`waveforms`](../waveform/) mainly focus on the first point described in [Introduction to QOS](../#introduction-to-qos).
- [`quarkstudio`](../quark/) mainly focus on the second, third, and fourth points described in [Introduction to QOS](../#introduction-to-qos)


### **How to start**
<!-- For instructions on how to use SystemQ, please refer to [Usage](https://quarkstudio.readthedocs.io/en/latest/usage/) -->

To use SystemQ, the following basic requirements need to be met.
<div class="result" markdown>
???+ warning "Requirements"
    <!-- ![SystemQ](image/aniatom.gif){ align=right width="150"} -->
    <!-- |:material-git: [git](https://git-scm.com/)|~| -->

    |name|version|
    |---|---|
    |:material-language-python: [python](https://python.org)|>=3.11|
</div>

First, download [**SystemQ**](https://gitee.com/baqis/systemq.git), and it is highly recommended to use :material-git:[git](https://git-scm.com/). Then you can install and start using SystemQ from [**tutorial**](../code/tutorial/).
???+ note "Installation"
    ``` bash
    # clone systemq
    git clone https://gitee.com/baqis/systemq.git

    # install systemq and its dependencies
    cd systemq
    pip install -e.

    # update if needed
    quark update --server
    quark update --studio
    ```

???+ warning "systemq"
    **Make sure that systemq has been installed succesfully(run `pip show systemq` to check)**


:material-email: Contact [fengyl@baqis.ac.cn]()