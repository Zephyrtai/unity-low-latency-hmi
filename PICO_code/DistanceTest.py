from machine import Pin
import time

# 1.Initialize
launch = Pin(3, Pin.OUT)
echo = Pin(2, Pin.IN)

start_time = 0
duration = 0

# Interrupt ReQuest: 当 Echo 引脚电平变化时，调用此中断回调函数 
def echo_handler(pin): # 参数驱动
    global start_time, duration #告诉函数，此变量是在外面定义的，我要在函数内部修改它的值
# ***有跳变时，才会记录***
    if pin.value() == 1:
        start_time = time.ticks_us()
    else:
        end_time = time.ticks_us()
        duration = time.ticks_diff(end_time, start_time)

# 绑定中断: 关注上升沿和下降沿（IRQ_RISING | IRQ_FALLING）
echo.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler = echo_handler)

# --- main ---
while True:
    # Trigger distance measurement
    launch.low()
    launch.sleep_us(2)
    launch.high
    launch.sleep_us(10)
    launch.low()

    if duration > 0:
        distance = duration * 0.034 / 2
        print(f"The distance is: {distance:2.f} cm")

    time.sleep(0.2) # 20Hz 的频率发送