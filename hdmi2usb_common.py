#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Tool to figure find the USB device that a board is available at.

This is a complicated process as the FX2 is software configurable and hence
could end up under many different VID:PID names based on what firmware is
currently loaded onto it.
"""

import os
from collections import namedtuple
import logging

PathBase = namedtuple('PathBase', ['bus', 'address'])
class Path(PathBase):
    def __init__(self, *args, **kw):
        PathBase.__init__(self, *args, **kw)
        assert os.path.exists(self.path), "%r %r" % (self.path, self)

    @property
    def path(self):
        return '/dev/bus/usb/%03i/%03i' % (self.bus, self.address)

    def __str__(self):
        return self.path

    def __cmp__(self, other):
        if isinstance(other, Path):
            return cmp(self.path, other.path)
        return cmp(self.path, other)

SYS_ROOT = '/sys/bus/usb/devices'

def get_path_from_sysdir(dirpath):
    buspath = os.path.join(dirpath, 'busnum')
    devpath = os.path.join(dirpath, 'devnum')
    if not os.path.exists(buspath):
        logging.info("Skipping %s (no busnum)", dirname)
        return None
    if not os.path.exists(devpath):
        logging.info("Skipping %s (no devnum)", dirname)
        return None

    busnum = int(open(buspath, 'r').read().strip())
    devnum = int(open(devpath, 'r').read().strip())

    return Path(bus=busnum, address=devnum)

def create_sys_mapping():
    # 1-1.3.1  --> (Device)    bus-port.port.port
    # 1-0:1.0  --> (Interface) bus-port.port.port:config.interface
    # usb1     --> bus<number>

    devices = {}
    interfaces = {}

    dirs = list(sorted(os.listdir(SYS_ROOT)))
    for dirname in dirs:
        dirpath = os.path.join(SYS_ROOT, dirname)
        if ":" in dirname:
            continue
        path = get_path_from_sysdir(dirpath)
        assert path
        devices[dirpath] = path
        assert path not in interfaces
        interfaces[path] = [dirpath]

    for dirname in dirs:
        dirpath = os.path.join(SYS_ROOT, dirname)
        if ":" not in dirname:
            continue

        device, interface = dirname.split(':')
        if device.endswith('-0'):
            device = "usb%s" % (device[:-2])

        devpath = os.path.join(SYS_ROOT, device)
        assert os.path.exists(devpath)
        assert devpath in devices

        interfaces[devices[devpath]].append(dirpath)

    return interfaces


def find_sys(path, mapping={}):
    if not mapping:
        mapping.update(create_sys_mapping())
    return mapping[path]


def test_libusb_and_lsusb_equal():
    libusb_devices = find_usb_devices_libusb()
    lsusb_devices = find_usb_devices_lsusb()
    for libobj, lsobj in zip(sorted(libusb_devices), sorted(lsusb_devices)):
        print "%s -- lib: %-40s ls: %-40s -- %-40s  drivers: %s" % (libobj.path, libobj, lsobj, find_sys(libobj.path)[0], lsobj.drivers())
        assert libobj.vid == lsobj.vid, "%r == %r" % (libobj.vid, lsobj.vid)
        assert libobj.pid == lsobj.pid, "%r == %r" % (libobj.pid, lsobj.pid)
        if libobj.serial:
            assert libobj.serial == lsobj.serial, "%r == %r" % (libobj.serial, lsobj.serial)
        assert libobj.path == lsobj.path, "%r == %r" % (libobj.path, lsobj.path)

        lsobj_inuse = lsobj.inuse()
        libobj_inuse = libobj.inuse()
        if libobj_inuse is not None:
            assert libobj_inuse == lsobj_inuse, "%r == %r" % (libobj_inuse, lsobj_inuse)


test_libusb_and_lsusb_equal()

BOARD_TYPES = ['opsis', 'atlys']
BOARD_NAMES = {
    'atlys': "Digilent Atlys",
    'opsis': "Numato Opsis",
    }
BOARD_STATES = ['unconfigured', 'jtag', 'serial', 'operational']

USBJTAG_MAPPING = {
    'hw_nexys': 'atlys',
    'hw_opsis': 'opsis',
    }
USBJTAG_RMAPPING = {v:k for k,v in USBJTAG_MAPPING.items()}

Board = namedtuple("Board", ["dev", "type", "state"])


import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--no-modify', help="Don't modify the state of the system in any way.")

parser.add_argument('--mac', help='Find board with the given MAC address.')
parser.add_argument('--dna', help='Find board with the given Device DNA.')
parser.add_argument('--position', help="""Find board using a given position in the USB structure.
Example:
 1-2.3 - Bus 1, Port 2 (which is a hub), Port 3
 5-6.7.8 - Bus 5, Port 2 (which is a hub), Port 7 (which is a hub), Port 8 (which is a hub)

While this *should* be static across reboots, but sadly on some machines it isn't :(
""")

parser.add_argument('--get-usbfs', help='Return the /dev/bus/usb path for a device.')
parser.add_argument('--get-sysfs', help='Return the /sys/bus/usb/devices path for a device.')

parser.add_argument('--get-state', help='Return the state the device is in. Possible states are: %r' % BOARD_STATES)
parser.add_argument('--get-video-device', help='Get the primary video device path.')
parser.add_argument('--get-serial-device', help='Get the serial device path.')

parser.add_argument('--use-hardware-serial', help='Use the hardware serial port on the Atlys board.')

parser.add_argument('--load-firmware', help='Load the firmware file onto the device.')

boards = []
for device in find_usb_devices_lsusb():
    # Digilent Atlys board with stock "Adept" firmware
    # Bus 003 Device 019: ID 1443:0007 Digilent Development board JTAG
    if device.vid == 0x1443 and device.pid == 0x0007:
        boards.append(Board(dev=device, type="atlys", state="unconfigured"))

    # The Numato Opsis will boot in the following mode when the EEPROM is not set up correctly.
    # Bus 003 Device 091: ID 04b4:8613 Cypress Semiconductor Corp. CY7C68013 EZ-USB FX2 USB 2.0 Development Kit
    elif device.vid == 0x04b4 and device.pid == 0x8613:
        boards.append(Board(dev=device, type="opsis", state="unconfigured"))

    # Boards loaded with the ixo-usb-jtag firmware from mithro's repo
    # https://github.com/mithro/ixo-usb-jtag
    # Bus 003 Device 090: ID 16c0:06ad Van Ooijen Technische Informatica 
    elif device.vid == 0x16c0 and device.pid == 0x06ad:
        if device.serial not in USBJTAG_MAPPING:
            logging.warn("Unknown usb-jtag device!")
            continue
        boards.append(Board(dev=device, type=USBJTAG_MAPPING[device.serial], state="usbjtag"))


for board in boards:
    print "%s as %s at %s" % (
        BOARD_NAMES[board.type],
        board.state,
        board.dev.path,
        )
    if board.dev.inuse():
        print " Board is currently used by drivers %s" % (board.dev.drivers(),)
        board.dev.detach()

    if board.state == "unconfigured":
        print " Configure with 'fxload -t fx2lp -D %s -I %s'" % (
            board.dev.path,
            "%s.hex" % USBJTAG_RMAPPING[board.type],
            )


"""

# Exar USB-UART device on the Digilent Atlys board
# Bus 003 Device 018: ID 04e2:1410 Exar Corp. 
# Driver at git+ssh://github.com/mithro/exar-uart-driver.git
if dev.driver() != "vizzini":
  # Need to install driver...
  pass



  - Digilent Atlys board loaded with Nero-USB JTAG firmware
  - Digilent Atlys board loaded with MakeStuff firmware
  - Digilent Atlys board loaded with HDMI2USB "unconfigured" firmware
  - Digilent Atlys board loaded with HDMI2USB "configured" firmware

  - Unconfigured Cypress FX2, could be a Numato Opsis

  - Numato Opsis board with no FX2 firmware loaded
  - Numato Opsis board loaded with Nero-USB JTAG firmware
  - Numato Opsis board loaded with MakeStuff firmware
  - Numato Opsis board loaded with HDMI2USB firmware

"""
