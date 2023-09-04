from enum import Enum, auto

CLOUD_ID = 0
CLOUD_IP = "0.0.0.0"
TCP_PORT = 0
WEBSOCK_TCP_PORT = 0

BUFFER_SIZE = 1024
DATAPACKET_SIZE = 64
NODE_INFO_BYTE_ARR_SIZE = 6


class NODE_CMD(Enum):
    """
    0 - Hello/HeartBeatPacket
    1 - LCC Advertisement
    2 - Device Advertisement
    3 - CONNECT
    4 - COMFIRM
    5 - REJECT
    6 - CONTROL
    7 - ReqDevList
    """

    HELLO = 0
    LCCADVERT = 1
    DEVADVERT = 2
    CONNECT = 3
    COMFIRM = 4
    REJECT = 5
    CONTROL = 6
    REQDEVLIST = 7
    MAX = auto()


class SYSTEM_ID(Enum):
    """
    1 - NodeSystem
    """

    NODESYS = 1
    END = auto()
