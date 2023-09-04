from threading import Thread, Timer
from collections import deque

import sys
import socketserver
import time
import struct
import socket

sys.path.append("..")

# self-module
from module.common import *
from module.node_system import *
from main import IotServer


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        addr = self.client_address[0]
        self.server.network_sys.add_sock((addr, self.request))

        while self.server.network_sys.get_status():
            # self.request is the TCP socket connected to the client
            try:
                data = self.request.recv(1024)
            except socket.timeout:
                continue
            except OSError:
                print("{} disconnect...".format(addr))
                break

            if not data:
                print("{} peer disconnect...".format(addr))
                break

            # client_address: (ip, port)
            # print(self.request)
            print("{} wrote:".format(addr))
            # print(str(data, encoding="utf-8"))

            # add to queue wait for process
            pack = (addr, self.request, data)
            self.server.network_sys.append_net_packet(pack)

        # clean
        self.server.network_sys.del_sock_by_ip(addr)


class MTCPServer(socketserver.TCPServer):
    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        bind_and_activate: bool = True,
        # (NetworkSystem, )
        args: tuple = None,
    ):
        self.allow_reuse_address = True
        socketserver.TCPServer.__init__(
            self, server_address, RequestHandlerClass, bind_and_activate
        )
        self.network_sys: NetworkSystem = args[0]


class MThreadingTCPServer(socketserver.ThreadingMixIn, MTCPServer):
    pass


# is still need this?
class NetPacketHandler(Thread):
    def __init__(self):
        Thread.__init__(self)


class NetworkSystem(Thread):
    """
    NetworkSystem
    """

    def __init__(self, server, node_sys, tcp_ip, tcp_port) -> None:
        Thread.__init__(self)
        #
        self.status = False
        self.server: IotServer = server
        self.node_system: NodeSystem = node_sys
        # tcp
        self.ip = tcp_ip
        self.port = tcp_port
        self.tcp_handle = MThreadingTCPServer(
            (self.ip, self.port), TCPHandler, args=(self,)
        )
        # network packets queue, packet struct: ('ip', socket, data)
        self.netpacket_queue = deque()
        # {"ip": socket}
        self.sock_map = {}

    def append_net_packet(self, netpack: tuple):
        """
        @netpack: ('ip', socket, data)
        @return: None
        """
        if not netpack or type(netpack) is not tuple:
            print(
                "[NetworkSystem::append_net_packet] Got invalid args, expect 1 tuple! "
            )
            return

        # TODO: multi-thread unsafe
        self.netpacket_queue.append(netpack)

    def get_net_packet(self):
        """
        @return: ('ip', socket, data)
        """
        packet = None

        # TODO: multi-thread unsafe
        try:
            packet = self.netpacket_queue.pop()
        except IndexError:
            pass

        return packet

    def add_sock(self, t: tuple):
        """
        @t: (ip, socket)
        """
        if not t or type(t) is not tuple or len(t) < 2:
            return

        self.sock_map[t[0]] = t[1]

    def get_sock_by_ip(self, ip: str):
        if not ip or type(ip) is not str or ip not in self.sock_map:
            return

        return self.sock_map[ip]

    def del_sock_by_ip(self, ip: str):
        if not ip or type(ip) is not str or ip not in self.sock_map:
            return

        del self.sock_map[ip]

    def get_status(self) -> bool:
        return self.status

    def stop(self):
        self.status = False

    def run_packet_hdler(self):
        while self.status:
            pack = self.get_net_packet()

            if not pack or len(pack) < 3 or len(pack[2]) < 3:
                time.sleep(1)
                continue

            # get data from tuple pack
            data = pack[2]
            byte_arr = bytearray(data)
            # (len, systemid, )
            res: tuple = struct.unpack_from("=HB", byte_arr, 0)
            print("[NetworkSystem] Recv NetPacket Len: ", res[0])
            systemid = res[1]

            if systemid < SYSTEM_ID.NODESYS.value or systemid >= SYSTEM_ID.END.value:
                print("[NetworkSystem] Recv unknow system id!")
                continue

            if systemid == SYSTEM_ID.NODESYS.value:
                self.node_system.append_NetPacket((pack[0], pack[1], data[3:]))

    def run_tcp_hdler(self):
        self.tcp_handle.serve_forever()

    def run(self):
        self.status = True
        # run netpacket handle thread
        packet_handle = Thread(target=self.run_packet_hdler)
        packet_handle.start()
        # run tcp request handle thread
        tcp_handle = Thread(target=self.run_tcp_hdler)
        tcp_handle.start()

        while self.status:
            time.sleep(3)
            print("network running...")
            pass

        # clean
        self.tcp_handle.shutdown()
        # self.tcp_handle.server_close()

        print("Exit NetworkSystem.")
