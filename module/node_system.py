from threading import Thread, Timer
from collections import deque

import time
import struct
import socket

# self-module
from module.common import *
from main import IotServer


# Node dev struct data
class DevInfo:
    def __init__(self, dev_id) -> None:
        self.dev_id = dev_id
        self.name = ""
        self.ip_addr = "0.0.0.0"
        self.is_live = 0
        self.last_respon = 0
        self.sock: socket = None
        # heartbeat
        self.rcv_heartbeat_flag = 0
        self.heartbeat_timer = None
        self.check_heartbeat_timer = None


class NodeSystem(Thread):
    def __init__(self, server) -> None:
        Thread.__init__(self)
        #
        self.ser: IotServer = server
        self.status = False
        # netpack data struct: (ip, sock, data)
        self.netpack_queue = deque()
        # dev info map
        self.dev_info_map = {}
        self.set_CMD_action()

    def set_CMD_action(self):
        self.CMD_Action = list(self.do_nothing for i in range(NODE_CMD.MAX.value))
        self.CMD_Action[NODE_CMD.CONNECT.value] = self.do_connect
        self.CMD_Action[NODE_CMD.COMFIRM.value] = self.do_comfirm
        self.CMD_Action[NODE_CMD.CONTROL.value] = self.do_control
        self.CMD_Action[NODE_CMD.REQDEVLIST.value] = self.do_reqDevlist

    def append_NetPacket(self, pack: tuple):
        """
        @pack: (ip, sock, data)
        """
        if not pack or type(pack) is not tuple:
            print(
                "[NodeSystem::append_NetPacket](ERROR) Got invalid args, expect 1 tuple! "
            )
            return

        self.netpack_queue.append(pack)

    def get_Netpacket(self):
        """
        @return (ip, sock, data) or None
        """
        packet = None

        # TODO: multi-thread unsafe
        try:
            packet = self.netpack_queue.pop()
        except IndexError:
            pass

        return packet

    def get_dev_by_id(self, dev_id: int):
        if not dev_id or type(dev_id) is not int or dev_id not in self.dev_info_map:
            return

        return self.dev_info_map[dev_id]

    def get_dev_by_ip(self, ip: str):
        if not ip or type(ip) is not str:
            return

        for dev_id, dev_info in self.dev_info_map.items():
            if dev_info.ip_addr == ip:
                return (dev_id, dev_info)

    def get_dev_list(self):
        dev_list = []

        for dev_id, dev_info in self.dev_info_map.items():
            dev_list.append((dev_id, dev_info))

        return dev_list

    def get_dev_count(self):
        return len(self.dev_info_map)

    def del_dev(self, dev_id):
        pass

    def disconn_dev(self, dev_id, call_from_net=0):
        dev_info: DevInfo = self.get_dev_by_id(dev_id)

        if not dev_info:
            return

        dev_info.ip_addr = "0.0.0.0"
        dev_info.is_live = 0

        try:
            dev_info.sock.shutdown(socket.SHUT_RDWR)
            dev_info.sock.close()
        except OSError:
            pass

        dev_info.sock = None

        if dev_info.heartbeat_timer:
            dev_info.heartbeat_timer.cancel()
            dev_info.heartbeat_timer = None

        if dev_info.check_heartbeat_timer:
            dev_info.check_heartbeat_timer.cancel()
            dev_info.check_heartbeat_timer = None

        print(
            "[NodeSystem::disconn_dev](WARNING) Disconnect device: {}, id: {}, ip: {}".format(
                str(dev_info.name, encoding="utf-8"), dev_info.dev_id, dev_info.ip_addr
            )
        )

    def heartbeat_cb(self, dev_info: DevInfo):
        print("send heartbeat!")
        if not dev_info.is_live or not dev_info.sock:
            return

        heartbeat = bytearray(DATAPACKET_SIZE)
        struct.pack_into(
            "=HBL", heartbeat, 0, DATAPACKET_SIZE, NODE_CMD.HELLO.value, CLOUD_ID
        )

        print(heartbeat)

        dev_info.sock.sendall(heartbeat)
        # start the timer to check whether recv dev heartbeat reply
        dev_info.check_heartbeat_timer = Timer(
            10, self.check_heartbeat_flag_cb, (dev_info,)
        )
        dev_info.check_heartbeat_timer.start()
        # start the timer waiting for next time send a heartbeat packet
        dev_info.heartbeat_timer = Timer(25, self.heartbeat_cb, (dev_info,))
        dev_info.heartbeat_timer.start()

    def check_heartbeat_flag_cb(self, dev_info: DevInfo):
        print("check heartbeat rcv flag!")
        if not dev_info.rcv_heartbeat_flag:
            print(
                "[NodeSystem](INFO) Device: {}, id: {}, ip: {} lost the connection !".format(
                    str(dev_info.name, encoding="utf-8"),
                    dev_info.dev_id,
                    dev_info.ip_addr,
                )
            )
            dev_info.sock.shutdown(socket.SHUT_RDWR)
            dev_info.sock.close()
            self.disconn_dev(dev_info.dev_id)
            return

        dev_info.rcv_heartbeat_flag = 0

    # CMD action
    def do_nothing(self, pack):
        pass

    def do_hello(self, pack):
        pass

    def do_connect(self, pack):
        ip = pack[0]
        sock = pack[1]
        byte_arr = pack[2]
        # (dev_id, dev_name )
        t: tuple = struct.unpack_from("=B4s", byte_arr, 0)
        dev_id = t[0]
        dev_name = t[1]

        # update dev info
        dev_info: DevInfo = self.get_dev_by_id(dev_id)

        if not dev_info:
            print("[NodeSystem](INFO) New Device connect...")
            dev_info = DevInfo(dev_id)
            self.dev_info_map[dev_info.dev_id] = dev_info
        else:
            if dev_info.is_live:
                print(
                    "[NodeSystem](WARNING) The device id: {}, name: {} is connected, update connection...".format(
                        dev_info.dev_id, str(dev_info.name, encoding="utf-8")
                    )
                )
                self.disconn_dev(dev_id)

        dev_info.dev_id = dev_id
        dev_info.name = dev_name
        dev_info.ip_addr = ip
        dev_info.is_live = 1
        dev_info.sock = sock

        # start heartbeat timer
        # Timer
        dev_info.heartbeat_timer = Timer(
            25,
            self.heartbeat_cb,
            (dev_info,),
        )
        dev_info.heartbeat_timer.start()

        print(
            "[NodeSystem](INFO) Device id: {}, name: {}, ip: {}, connected successfully!".format(
                dev_info.dev_id, str(dev_info.name, encoding="utf-8"), dev_info.ip_addr
            )
        )

        # reply
        reply = bytearray(DATAPACKET_SIZE)
        struct.pack_into(
            "=HBBB",
            reply,
            0,
            DATAPACKET_SIZE,
            NODE_CMD.COMFIRM.value,
            0,
            NODE_CMD.CONNECT.value,
        )
        # print("Check do_connect Reply packet: ", reply)
        sock.sendall(reply)

    def do_comfirm(self, pack):
        print("[NodeSystem::do_comfirm](INFO) Recv comfirm cmd...")

        ip = pack[0]
        sock = pack[1]
        byte_arr = pack[2]
        # (err_code, reply_cmd )
        t: tuple = struct.unpack_from("=BB", byte_arr, 0)
        err_code = t[0]
        reply_cmd = t[1]

        if reply_cmd == NODE_CMD.HELLO.value:
            # (dev_id,)
            dev_id = struct.unpack_from("=B", byte_arr, 2)[0]
            dev_info: DevInfo = self.get_dev_by_id(dev_id)
            dev_info.rcv_heartbeat_flag = 1

        else:
            print("[NodeSystem::do_comfirm](INFO) Unknow reply cmd!")

    def do_control(self, pack):
        ip = pack[0]
        sock = pack[1]
        byte_arr = pack[2]
        # (dev_id, pin, level )
        t: tuple = struct.unpack_from("=BBB", byte_arr, 0)
        dev_id = t[0]
        pin = t[1]
        lv = t[2]

        dev_info: DevInfo = self.get_dev_by_id(dev_id)

        if not dev_info:
            print("[NodeSystem::do_control](INFO) Unknow device id!")
            # TODO: need to reply to LCC
            return

        if not dev_info.is_live or not dev_info.sock:
            print(
                "[NodeSystem::do_control](INFO) Device id: {}, name: {} is offline!".format(
                    dev_info.dev_id,
                    str(dev_info.name, encoding="utf-8"),
                )
            )
            # TODO: need to reply to LCC
            return

        # reply
        reply = bytearray(DATAPACKET_SIZE)
        struct.pack_into(
            "=HBBBB",
            reply,
            0,
            DATAPACKET_SIZE,
            NODE_CMD.CONTROL.value,
            dev_id,
            pin,
            lv,
        )
        print("Check do_control Reply packet: ", reply)
        dev_info.sock.sendall(reply)

    def do_reqDevlist(self, pack):
        ip = pack[0]
        sock = pack[1]
        # byte_arr = pack[2]
        # get dev list
        # reply
        reply = bytearray(DATAPACKET_SIZE)
        struct.pack_into(
            "=BBB",
            reply,
            0,
            NODE_CMD.COMFIRM.value,
            0,
            NODE_CMD.REQDEVLIST.value,
        )

        # dev count
        struct.pack_into("=B", reply, 3, self.get_dev_count())
        # dev list
        dev_list = self.get_dev_list()
        # TODO: Check that dev data is out of DATAPACKET size
        offset = 4
        for dev_id, dev_info in dev_list:
            struct.pack_into(
                "=B4sB", reply, offset, dev_id, dev_info.name, dev_info.is_live
            )
            offset += 6
        print("Check do_reqDevlist Reply packet: ", reply)
        sock.sendall(reply)

    def stop_all_dev_connection(self):
        for dev_id, dev_info in self.dev_info_map.items():
            self.disconn_dev(dev_id)

    def stop(self):
        self.status = False

    def run(self):
        self.status = True

        while self.status:
            # pack: (ip, sock, data)
            pack = self.get_Netpacket()

            if not pack:
                time.sleep(1)
                continue

            data = pack[2]
            byte_arr = bytearray(data)
            # (cmd, ...)
            t: tuple = struct.unpack_from("=B", byte_arr, 0)
            cmd = t[0]

            if cmd < NODE_CMD.HELLO.value or cmd >= NODE_CMD.MAX.value:
                print("[NodeSystem] Recv unknow CMD!")
                continue

            self.CMD_Action[cmd]((pack[0], pack[1], byte_arr[1:]))

        # clean
        self.stop_all_dev_connection()
        print("Exit NodeSystem.")
