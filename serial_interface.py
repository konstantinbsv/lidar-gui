import serial
import sys

ser = None


def init_serial(port, baudrate):
    global ser
    # initialize serial
    ser = serial.Serial()

    # configure serial port
    ser.port = port
    ser.baudrate = baudrate

    # open serial port
    try:
        ser.open()
    except serial.serialutil.SerialException as e:
        print(e)
        sys.exit(1)


def get_serial_data():
    global ser
    if ser is not None:
        # get data from serial
        try:
            line = ser.readline().decode('utf-8')
        except UnicodeDecodeError:
            print('Unicode decoding error - waiting for next line')
            line = '0,0.0\r\n'

        # process serial data
        degrees, distance = line.strip().split(',')
        distance = float(distance)                      # convert distance string to float
        degrees = int(degrees)
    else:
        degrees = 0
        distance = 0

    return degrees, distance


def close():
    global ser
    if ser is not None:
        ser.close()

