# The Toolbox
from machine import Pin
import machine
import json
import network
import socket
import time
import random
import sys

# 1. The Handshake
def wifi_connect():
    wifi_name = "Wi Believe I Can Fi"
    password = "63z5vg6w"
    #安全性: 真实项目中，直接把 WiFi 密码写在代码里是不安全的，通常会放在一个单独的 config.py 文件中

    # ①.创建“工作站模式”（连接路由器）开发板像手机一样连接路由器的信号
    wlan = network.WLAN(network.STA_IF) # STA_IF：Station模式
    # ②. Enable the network adapter
    wlan.active(True)
    # ③. Start connecting to WiFi
    wlan.connect(wifi_name, password)
    # ④. 阻塞等待（重连） 确保网络通畅前代码不会往下运行 Block until connected
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        print("Connecting to Wifi...")
        time.sleep(1)
        timeout -= 1

    if not wlan.isconnected():
        print("Failed to connect! Stopping...")
        sys.exit()

    print("Connected! IP: ", wlan.ifconfig()[0])

# 2. The Delivery Method
UDP_IP = "192.168.101.8"
UDP_PORT = 5005

# Create a UDP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#AF_INT：IPv4:Address Family - Internet Protocol v4； SOCK.DGRAM:UDP Protocol
sock.setblocking(False) # 【核心】设置为 Non-Blocking 非阻塞模式
# ***【举一反三】: 以后遇到任何涉及外部设备 (网卡、蓝牙、串口)的操作，都要找找有没有 setblocking(False) 这个选项***

# 3. Collect data
# ①.Initialize
launch = Pin(3, Pin.OUT)
echo = Pin(2, Pin.IN)

start_time = 0
duration = 0
last_dis = 0.0
data_ready = False

# Interrupt ReQuest: 当 Echo 引脚电平变化时，调用此中断回调函数 
def echo_handler(pin): # 参数驱动
    #global:告诉函数，此变量是在外面定义的，我要在函数内部修改它的值
    global start_time, duration, data_ready
# ***有跳变时，才会记录***
    if pin.value() == 1:
        start_time = time.ticks_us()
    else:
        end_time = time.ticks_us()
        duration = time.ticks_diff(end_time, start_time)
        data_ready = True #【标志位】告诉主程序：数据写好了

# ②.【Bound Interrupt】: 关注上升沿和下降沿（IRQ_RISING | IRQ_FALLING）
echo.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler = echo_handler)

def trigger_sensor(): # 只负责触发
    global data_ready
    data_ready = False # 触发前先重置标志，确保读到的是“这次”的数据

    # Trigger distance measurement
    launch.low()
    time.sleep_us(2) # us：微秒
    launch.high()
    time.sleep_us(10) # Boost sensor
    launch.low()

# 4. The heartbeat (Send data)
# 记录上次发送的 timestamp, 用于[控制频率]
last_send_tick = time.ticks_ms()
last_trigger_tick = time.ticks_ms()

wifi_connect()

while True:
    current_tick = time.ticks_ms()

    # 1. 周期性触发传感器(once every 100ms)
    if time.ticks_diff(current_tick, last_trigger_tick) >= 200:
        trigger_sensor()
        last_trigger_tick = current_tick

    # 2. Check whether the data has been updated by Interrupt ReQuest
    if data_ready:
        # 进入临界保护区: [保护共享变量**读取**]，防止被中断回调函数修改
        # 专业术语：原子性保护的嵌套
        state = machine.disable_irq() # 关掉中断“插队”功能，暂停保存状态
        current_duration = duration #[使用本地变量进行计算（此时计算再久也不会被干扰）] **【加快速度，给完变量就退出。不用等待计算结果】**
        data_ready = False
        machine.enable_irq(state) # 恢复中断(还原到暂停时的状态)
        # **保证了无论进入函数前 中断是开还是关，退出函数后都会回到原来的样子**

        last_dis = current_duration * 0.034 / 2

    # 3. 周期性发送网络数据 (不影响测距频率)
    if time.ticks_diff(current_tick, last_send_tick) >= 200:# 20Hz 发送
        # ①. Json format（包装成字典）
        data = {
            "speed": round(random.uniform(0,30), 2),
            "raw_distance": round(last_dis, 2)
        }
        # ②. 序列化：将字典转化为字符串
        message = json.dumps(data)
        # ③.【发送】:转换为字节流 .encode() {二进制字节(Bytes)} (无法直接发送字符串)
        try:
            sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
            print("Sent:", message)
        except Exception as e:  # 对应上面 setblocking(False)，捕获网络异常（如网络波动导致发送失败）
            #如果网络发不出去，没关系，直接跳过，打印提醒或干脆保持沉默
            #保证下一行测距代码能 按时运行
            print("Network bussy, skipping this packet.")
            pass  # 避免网络波动卡死主循环