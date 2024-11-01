"""本模块存放所有设备的驱动
1、所有驱动继承自BaseDriver，类名统一为Driver，并要求实现open/close/read/write四个方法。样板见VirtualDevice
2、所有厂家提供的底层库（如dll等），均放于driver/common内，各自新建文件夹分别放置（如Manufacturer）
"""