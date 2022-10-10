from array import array
from decimal import ROUND_FLOOR
from math import floor
from operator import add
import varint
from base64 import b64decode, b64encode
from pickle import APPEND
import numpy as np
import sys
if sys.version > '3':
    def _byte(b):
        return bytes((b, ))
else:
    def _byte(b):
        return chr(b)

def encode(number):
    """Pack `number` into varint bytes"""
    buf = b''
    while True:
        towrite = number & 0x7f
        number >>= 7
        if number:
            buf += _byte(towrite | 0x80)
        else:
            buf += _byte(towrite)
            break
    return buf
data = {'data': [[0.04, [255, 255, 255], 1], [0.79, [255, 255, 255], 1], [1.04, [0, 0, 0], 1], [2.04, [0, 0, 0], 1], [2.29, [17, 17, 17], 1], [3.04, [17, 17, 17], 1], [3.29, [255, 53, 171], 1], [3.79, [255, 205, 234], 1], [4.04, [255, 255, 255], 1], [4.79, [255, 255, 255], 1], [5.04, [0, 0, 0], 1], [5.79, [0, 0, 0], 1], [6.04, [17, 17, 17], 1], [7.04, [17, 17, 17], 1], [7.29, [14, 255, 5], 1], [7.79, [184, 255, 181], 1], [8.04, [255, 255, 255], 1], [8.79, [255, 255, 255], 1], [9.04, [0, 0, 0], 1], [9.79, [0, 0, 0], 1], [10.04, [17, 17, 17], 1], [11.04, [17, 17, 17], 1], [11.29, [255, 66, 176], 1], [11.79, [255, 217, 239], 1], [12.04, [255, 255, 255], 1], [12.79, [255, 255, 255], 1], [13.04, [0, 0, 0], 1], [13.79, [0, 0, 0], 1], [14.04, [17, 17, 17], 1], [15.04, [17, 17, 17], 1], [15.29, [14, 255, 5], 1], [15.79, [14, 255, 5], 1], [16.04, [0, 0, 0], 1], [16.54, [0, 0, 0], 1], [16.79, [14, 255, 5], 1], [17.29, [14, 255, 5], 1], [17.54, [255, 255, 255], 1], [18.04, [255, 255, 255], 1], [18.29, [46, 48, 55], 1], [18.79, [46, 48, 55], 1], [19.04, [255, 255, 255], 1], [19.54, [255, 255, 255], 1], [19.79, [46, 48, 55], 1], [20.29, [46, 48, 55], 1], [20.54, [0, 0, 0], 1], [21.29, [0, 0, 0], 1], [21.54, [255, 2, 152], 1], [22.04, [255, 2, 152], 1], [22.29, [16, 13, 12], 1], [22.79, [207, 163, 153], 1], [23.04, [178, 141, 132], 1], [23.29, [26, 20, 19], 1], [23.54, [142, 112, 104], 1], [23.79, [182, 143, 134], 1], [24.04, [85, 67, 63], 1], [24.29, [0, 0, 0], 1], [24.54, [167, 134, 126], 1], [24.79, [108, 90, 85], 1], [25.04, [132, 108, 102], 1], [25.29, [238, 188, 176], 1], [25.79, [34, 34, 34], 1], [26.29, [211, 12, 174], 1], [26.54, [255, 123, 196], 1], [26.79, [255, 45, 205], 1], [27.04, [255, 87, 200], 1], [27.29, [255, 185, 190], 1], [27.54, [255, 158, 193], 1], [28.29, [255, 6, 209], 1], [29.54, [255, 201, 188], 1], [30.29, [86, 3, 71], 1], [30.54, [21, 1, 18], 1], [30.79, [69, 2, 57], 1], [31.04, [53, 2, 44], 1], [31.29, [13, 0, 11], 1], [31.54, [31, 1, 26], 1], [31.79, [78, 3, 64], 1], [32.04, [86, 3, 71], 1], [32.29, [86, 3, 71], 1], [32.54, [22, 1, 18], 1], [33.29, [22, 1, 18], 1], [33.54, [56, 2, 46], 1], [34.29, [56, 2, 46], 1], [34.54, [86, 3, 71], 1], [35.42, [86, 3, 71], 1]], 'version': 1}
skybrush_output = "BygKDAIyCRENAiUI/zWrDQj/zeoZCwwCJgoMAiYJEQwCMggO/wUNCLj/tRkLDAImCgwCJgkRDAIyCP9CsA0I/9nvGQsMAiYKDAImCREMAjIIDv8FDQIZCgwCGQgO/wUNDAICGQsMAhkILjA3DQ0CGQoMAiYI/wKYDAIZCBANDA0Iz6OZGQiyjYQMCBoUEw0IjnBoDAi2j4YNCFVDPwwKDQinhn4MCGxaVQ0IhGxmDAjuvLANCSIZCNMMrhkI/3vEDAj/Lc0NCP9XyAwI/7m+DQj/nsEMCP8G0SYI/8m8PghWA0cmCBUBEgwIRQI5DQg1AiwMCA0ACw0IHwEaDAhOA0ANCFYDRwwCDQhAAjQMAiYIIgEcDAImCFYDRwwCLAA="
output = bytearray()
last_time = 0
last_color = np.array([-1, -1, -1])
white_color = np.array([255, 255, 255])
black_color = np.array([0, 0, 0])
add_duration_flag = 0
delay_flag = 1
first_time_flag = 1
have_half = 0
for item in data.get('data'):
    duration = round((item[0] - last_time) * 50)
    if (duration == 12):
        if have_half > 2:
            duration += 1
            have_half -= 2
    if (((item[0] - last_time) * 50) - duration == 0.5):
        have_half += 1
    if (add_duration_flag):
        if(first_time_flag):
            duration = duration + 2
            first_time_flag = 0
        output.extend(encode(duration))
        add_duration_flag = 0
    if(np.array_equal(last_color, [-1, -1, -1])):
        if (np.array_equal(item[1], white_color)):
            output.append(7)
        elif(np.array_equal(item[1], black_color)):
            output.append(6)
        else:
            output.append(4)
            output.append(item[1][0])
            output.append(item[1][1])
            output.append(item[1][2])
        add_duration_flag = 1
        delay_flag = 0
    elif(np.array_equal(item[1], last_color)):
        if (delay_flag):
            output.append(2)
            output.extend(encode(duration))
        else:
            delay_flag = 1
    elif (np.array_equal(item[1], white_color)):
        output.extend(b'\x0b')
        output.extend(encode(duration))
        delay_flag = 1
    elif (np.array_equal(item[1], black_color)):
        output.append(10)
        output.extend(encode(duration))
        delay_flag = 1
    elif(item[1][0] == item[1][1] == item[1][2]):
        output.extend(b'\t')
        output.append(item[1][0])
        add_duration_flag = 0
        output.extend(encode(duration))
        delay_flag = 1
    else:
        output.append(8)
        output.append(item[1][0])
        output.append(item[1][1])
        output.append(item[1][2])
        output.extend(encode(duration))
        add_duration_flag = 0
        delay_flag = 1
    last_time = item[0]
    last_color = item[1].copy()
output.append(0)
print("My output:")
print(bytes(output))
print(b64encode(output))
print("Expected: ")
print(bytes(b64decode(skybrush_output)))
print(skybrush_output)
print(varint.encode(12))
print(varint.decode_bytes(b'\n'))
print(round(12.5))
