import time

import psutil

pid = 8652
while True:
    process = psutil.Process(pid)
    mem = process.memory_info()
    with open("log.log", "a") as f:
        print(mem.rss, mem.vms, file=f)
    time.sleep(10)
