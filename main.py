# build-in lib
from threading import Thread

# self-module
from module.common import *
from module.network_system import *
from module.node_system import *


class IotServer:
    def __init__(self) -> None:
        # server config
        self.host = CLOUD_IP
        self.tcp_port = TCP_PORT
        self.cloud_id = CLOUD_ID

        # system
        self.node_sys: NodeSystem = NodeSystem(self)
        self.network_sys: NetworkSystem = NetworkSystem(
            self, self.node_sys, self.host, self.tcp_port
        )

    def set_config(self):
        pass

    def collect_stat(self):
        pass

    def start_tcp_server(self):
        self.network_sys.start()

    def run(self):
        # pre-do
        self.start_tcp_server()
        self.node_sys.start()

        while True:
            cmd = input()
            if cmd == "quit" or cmd == "exit":
                break

        # clean
        self.network_sys.stop()
        self.node_sys.stop()


def main():
    print("Run Server...")
    server = IotServer()
    server.run()
    print("Exit. Byebye")


if __name__ == "__main__":
    main()
