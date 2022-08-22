import subprocess,os
cmd="uuidgen"
uuid = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
uuid = uuid.decode("utf-8")
print(uuid)

import datetime
collection_time=3
current_time = datetime.datetime.now() 
time_duration = current_time - datetime.timedelta(minutes=collection_time)

start_ts = int(time_duration.timestamp())  
current_ts= int(datetime.datetime.now().timestamp())

print(current_ts,start_ts)
