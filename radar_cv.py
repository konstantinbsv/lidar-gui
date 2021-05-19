import math
import cv2
import numpy as np
import serial_interface
import sys
import getopt


# layout constants
MAX_RANGE = 100                 # default range to display on radar plot (cm)
PIXELS = 900                    # size of frame
X_PADDING = 50                  # pixels between last circle on radar and edge of frame
Y_PADDING = 40                  # pixels between last circle on radar and bottom of fame
BLIP_SIZE = 2                   # object size in pixels
CIRCLES = 4                     # number of circles on radar reticule
RADIAL_LINES = 6                # number of radial lines on reticule
TRAIL_LENGTH = 10               # number of scan lines to trail
LINE_FADE_FACTOR = 0.80         # fade per scan line trail
BLIP_FADE_FACTOR = 0.994        # how much objects fade with distance from scan line
BLIP_COLOR = (0, 77, 255)       # color of blip
CIRCLE_COLOR = (0, 22, 200)     # color of screen circles
SCAN_LINE_COLOR = (0, 77, 255)  # color of scan line
TEXT_COLOR = (0, 22, 200)       # color text on screen
DRAW_POSTERIOR_LINE = True      # draw line behind object
DRAW_ANTERIOR_LINE = True       # draw line in front of object

# debugging options (persistent)
DEBUG_DATA = False      # create fake data or use real serial data
SERIAL_OUTPUT = False   # display serial data to console

# initialize config variables with constants
debug_data = DEBUG_DATA
serial_output = SERIAL_OUTPUT
max_range = MAX_RANGE
draw_anterior_line = DRAW_ANTERIOR_LINE
draw_posterior_line = DRAW_POSTERIOR_LINE
com_port = 'COM10'  # default com port
baud_rate = 115200  # default baud rate
min_rand = 150      # min for random number generator (used only if generating debug data)
max_rand = 200      # max for random number generator

# get options from command line
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hvrfb:', ['com=', 'baud=', 'help', 'range=',
                                                      'debug', 'min_rand=', 'max_rand='])
except getopt.GetoptError as e:
    print(e)
    opts = [('-h', '')]

for opt, arg in opts:
    if opt in ('-h', '--help'):
        print(f'''radar_cv.py
  -h\t\t: displays this help (also --help)
  -v\t\t: shows live serial data
  -r <cm>\t: sets display range in centimeters (also --range), default = {MAX_RANGE}cm
  -f\t\t: disable show line for clear path in front of object
  -b\t\t: disable show line for blocked path behind object
  
  Serial Options:
  --com <com>\t: sets COM port (e.g COM9, COM10...), default = {com_port}
  --baud <baud>\t: sets baud rate (e.g. 9600), default = {baud_rate}
  
  Debug options:
  --debug\t  : displays random data instead of using serial
  --min_rand <cm> : minimum value for random number generator, default = {min_rand}cm
  --max_rand <cm> : maximum value for random number generator, default = {max_rand}cm''')
        sys.exit(0)
    elif opt == '-v':
        serial_output = True
    elif opt in ('-r', '--range'):
        max_range = float(arg)
    elif opt == '-f':
        draw_anterior_line = False
    elif opt == '-b':
        draw_posterior_line_line = False
    elif opt == '--com':
        com_port = arg
    elif opt == '--baud':
        baud_rate = arg
    elif opt == '--debug':
        debug_data = True
    elif opt == '--min_rand':
        min_rand = float(arg)
    elif opt == '--max_rand':
        max_rand = float(arg)

# initialize serial if not debugging
if not debug_data:
    serial_interface.init_serial(com_port, baud_rate)
    wait = 1    # wait time for OpenCV GUI
else:
    wait = 25
i_val = 0

img = np.zeros((int(PIXELS/2 + Y_PADDING), PIXELS, 3), np.uint8)     # black background (y, x, c_space)
x_center = int((img.shape[1])/2)
y_bottom = int(img.shape[0] - Y_PADDING)

# draw radar circles
font = cv2.FONT_HERSHEY_SIMPLEX
cv2.circle(img, (x_center, y_bottom), 1, CIRCLE_COLOR, 2, cv2.LINE_AA)    # center dot
radii = [0]*CIRCLES   # will store values of radii circles
for i in range(CIRCLES):
    # draw circles
    scale = (1 - i/CIRCLES)
    radii[i] = int((x_center - X_PADDING) * scale)
    cv2.circle(img, (x_center, y_bottom), radii[i], CIRCLE_COLOR, 1, cv2.LINE_AA)

# draw distance labels
cv2.rectangle(img, (0, int(y_bottom + Y_PADDING * 0.1)), (img.shape[1], img.shape[0]), (0, 0, 0), cv2.FILLED)
cv2.putText(img, '(cm)', (x_center+10, int(y_bottom + Y_PADDING * 0.75)), font, 0.5, TEXT_COLOR, 1, cv2.LINE_AA)
for i in range(CIRCLES):
    # range labels
    scale = (1 - i / CIRCLES)
    x_label = x_center + radii[i] - 20
    label = str(round(max_range * scale))
    cv2.putText(img, label, (x_label, int(y_bottom + Y_PADDING * 0.75)), font, 0.5, TEXT_COLOR, 1, cv2.LINE_AA)

# draw angle labels
if RADIAL_LINES > 0:
    for i in range(RADIAL_LINES+1):
        angle_scale = (1 - i / RADIAL_LINES)
        line_angle = round(angle_scale * 180)
        line_angle_rad = line_angle * math.pi/180
        m = 25*angle_scale
        x_label = int(x_center - m + (radii[0] + 10) * math.cos(line_angle_rad))  # x point of radar line
        y_label = int(y_bottom - (radii[0] + 10) * math.sin(line_angle_rad))  # y point of radar line
        label = str(round(line_angle))
        cv2.putText(img, label, (x_label, y_label), font, 0.5, TEXT_COLOR, 1, cv2.LINE_AA)


# data acquisition
def get_data():
    if debug_data:
        # fake data generator
        global i_val
        if int(i_val/181) % 2 == 0:
            deg = i_val % 181
        else:
            deg = 180 - i_val % 180

        i_val = i_val + 1   # increment
        # generate random distance
        dist = np.random.randint(min_rand, max_rand)
    else:
        # get data from serial interface
        deg, dist = serial_interface.get_serial_data()

    if serial_output:
        print(f'degrees={deg}\t distance={dist}')
    return deg, dist


def draw_scan_line(image, angle, l_color, x_start=x_center, y_start=y_bottom, x_end=None, y_end=None):
    angle = angle * math.pi/180                         # convert angle to radians
    if x_end is None:
        x_end = int(x_center + radii[0] * math.cos(angle))  # x point of radar line
    if y_end is None:
        y_end = int(y_bottom - radii[0] * math.sin(angle))  # y point of radar line
    cv2.line(image, (x_start, y_start), (x_end, y_end), l_color, 1, cv2.LINE_AA)


def draw_blip(angle, dist, b_color):
    angle = angle * math.pi / 180                       # convert to radians
    dist = dist * (radii[0]/max_range)                  # convert cm to pixels
    x_object = int(x_center + dist * math.cos(angle))   # x coordinate of object
    y_object = int(y_bottom - dist * math.sin(angle))   # y coordinate of object
    cv2.circle(frame, (x_object, y_object), BLIP_SIZE, b_color, cv2.FILLED, cv2.LINE_AA)
    return x_object, y_object


def draw_radial_lines(image, num_lines):
    if num_lines > 0:
        for line in range(num_lines+1):
            r_angle_scale = (1 - line / num_lines)
            r_line_angle = round(r_angle_scale * 180)
            draw_scan_line(image, r_line_angle, CIRCLE_COLOR)


# to store blip positions and colors [distance][color]
blips = [[0, (0, 0, 0)] for i in range(181)]
last_degrees = -1            # last degrees to determine direction of scan

# display graph with updates
while True:
    # get data
    degrees, distance = get_data()     # get data from serial function
    radians = degrees * math.pi/180     # convert degrees to radians

    frame = img.copy()  # create current frame

    # draw scan line and trail
    direction = degrees - last_degrees  # 1 = up; -1 = down
    line_color = SCAN_LINE_COLOR
    for j in range(TRAIL_LENGTH):
        angle_deg = degrees - direction * j                             # calculate scan line angle
        draw_scan_line(frame, angle_deg, line_color)                    # draw scan line
        line_color = tuple(LINE_FADE_FACTOR * c for c in line_color)    # fade line color

    # draw radial lines on reticule
    draw_radial_lines(frame, RADIAL_LINES)

    # update objects array with current object data
    # color is refreshed every time object distance is updated
    current = int(degrees)
    blips[current][0] = distance      # set distance
    blips[current][1] = BLIP_COLOR    # refresh color

    # draw objects
    for j in range(len(blips)):
        # get distance and color
        distance = blips[j][0]
        color = blips[j][1]

        # draw blip on screen
        x, y = draw_blip(j, distance, color)

        # draw line behind object
        if draw_anterior_line:
            c_front = (color[0], color[2], color[1])
            # if distance > max_range:
            #     draw_scan_line(frame, j, c_front)
            # else:
            draw_scan_line(frame, j, c_front, x_end=x, y_end=y)
        if draw_posterior_line & (distance < max_range):
            draw_scan_line(frame, j, color, x_start=x, y_start=y)

        # fade color after object has been accessed (each time it has been accessed)
        # this will fade object blips as their data gets more stale
        blips[j][1] = tuple(BLIP_FADE_FACTOR * c for c in color)

    # show frame
    cv2.imshow("Sonar Display", frame)
    if cv2.waitKey(wait) in (ord('q'), 0x1b):
        break

    # update last degree
    last_degrees = degrees

# close serial if not debugging
if not debug_data:
    serial_interface.close()
