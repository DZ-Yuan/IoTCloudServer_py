## TODO

1. 发送/回复Node信息时，不应该有NodeSystem直接回复，应该通过NetworkSystem发送回复

2. 当Node断开连接，需要通知到NodeSystem

    或者直接在NodeSystem中调用socket方法时加上try检查是否socket还存在



