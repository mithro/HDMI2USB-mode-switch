#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

from __future__ import print_function

import binascii
import crcmod
import ctypes
import enum
import math
import re
import sys

from utils import *

# Remove after https://bugs.python.org/issue19023 is fixed.
assert sys.byteorder == 'little'
ctypes.LittleEndianUnion = ctypes.Union


class DynamicLengthStructure(ctypes.LittleEndianStructure):
    r"""
    >>> class Test(DynamicLengthStructure):
    ...    _fields_ = [
    ...        ("b1",      ctypes.c_uint8),
    ...        ("crc8",    ctypes.c_uint8),
    ...        ("_len",    ctypes.c_uint8),
    ...        ("_data",   ctypes.c_ubyte * 0),
    ...    ]
    >>> assert ctypes.sizeof(Test) == 3

    >>> t1 = Test()
    >>> ctypes.sizeof(t1)
    3
    >>> t1._extra_size
    0
    >>> t1.b1
    0
    >>> t1.crc8
    0
    >>> t1.len
    0
    >>> t1._len
    0
    >>> t1.data[:]
    []
    >>> type(t1.data)
    <class '__main__.c_ubyte_Array_0'>
    >>> ctypes.sizeof(t1.data)
    0
    >>> t1.as_bytearray()
    bytearray(b'\x00\x00\x00')
    >>> # Changing normal value
    >>> t1.b1 = 0xa
    >>> t1.b1
    10
    >>> t1.as_bytearray()
    bytearray(b'\n\x00\x00')
    >>> # Increasing data length
    >>> t1.len = 1
    >>> ctypes.sizeof(t1)
    4
    >>> t1.data[:]
    [0]
    >>> type(t1.data)
    <class '__main__.c_ubyte_Array_1'>
    >>> ctypes.sizeof(t1.data)
    1
    >>> t1.as_bytearray()
    bytearray(b'\n\x00\x01\x00')
    >>> t1.data[0] = 0xf
    >>> t1.data[:]
    [15]
    >>> t1.as_bytearray()
    bytearray(b'\n\x00\x01\x0f')
    >>> # Increasing data length further
    >>> t1.len = 2
    >>> ctypes.sizeof(t1)
    5
    >>> t1.data[:]
    [15, 0]
    >>> t1.as_bytearray()
    bytearray(b'\n\x00\x02\x0f\x00')
    >>> t1.data[1] = 0xe
    >>> t1.data[:]
    [15, 14]
    >>> t1.as_bytearray()
    bytearray(b'\n\x00\x02\x0f\x0e')

    >>> # Test CRC calculation
    >>> t2 = Test()
    >>> # CRC doesn't change on CRC value
    >>> hex(t2.crc_calculate())
    '0x0'
    >>> t2.crc8 = 0xa
    >>> t2.crc8
    10
    >>> hex(t2.crc_calculate())
    '0x0'
    >>> # CRC changes on changing b1
    >>> t2.b1 = 1
    >>> t2.b1
    1
    >>> hex(t2.crc_calculate())
    '0x15'
    >>> # CRC changes on changing values in the data section
    >>> t2.len = 1
    >>> hex(t2.crc_calculate())
    '0x7e'
    >>> t2.data[0] = 1
    >>> hex(t2.crc_calculate())
    '0x79'
    >>> t2.crc_check()
    False
    >>> t2.crc_update()
    >>> hex(t2.crc8)
    '0x79'
    >>> t2.crc_check()
    True

    >>> class TestExtra(DynamicLengthStructure):
    ...    _fields_ = [
    ...        ("b1",      ctypes.c_uint8),
    ...        ("crc8",    ctypes.c_uint8),
    ...        ("_len",    ctypes.c_uint8),
    ...        ("b2",      ctypes.c_uint8),
    ...        ("_data",   ctypes.c_ubyte * 0),
    ...    ]
    >>> assert ctypes.sizeof(TestExtra) == 4
    >>> t3 = TestExtra()
    >>> ctypes.sizeof(t3)
    4
    >>> t3._extra_size
    1
    >>> t3.len
    0
    >>> t3._len
    1
    >>> t3.b2 = 0xf
    >>> t3.as_bytearray()
    bytearray(b'\x00\x00\x01\x0f')
    >>> t3.data[:]
    []
    >>> type(t3.data)
    <class '__main__.c_ubyte_Array_0'>
    >>> ctypes.sizeof(t3.data)
    0
    >>> t3.len = 1
    >>> ctypes.sizeof(t3)
    5
    >>> t3.data[:]
    [0]
    >>> type(t3.data)
    <class '__main__.c_ubyte_Array_1'>
    >>> ctypes.sizeof(t3.data)
    1
    >>> t3.as_bytearray()
    bytearray(b'\x00\x00\x02\x0f\x00')
    >>> t3.data[0] = 0xe
    >>> t3.data[:]
    [14]
    >>> t3.as_bytearray()
    bytearray(b'\x00\x00\x02\x0f\x0e')
    """
    _pack_ = 1

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if self._len == 0:
            self._len = self._extra_size

    @property
    def _extra_start(self):
        return self.__class__._len.offset+self.__class__._len.size

    @property
    def _extra_end(self):
        return self.__class__._data.offset

    @property
    def _extra_size(self):
        return self._extra_end - self._extra_start

    @property
    def len(self):
        return self._len - self._extra_size

    @len.setter
    def len(self, value):
        rsize = self._extra_end + value
        if ctypes.sizeof(self) < rsize:
            ctypes.resize(self, rsize)

        self._len = self._extra_size + value

    @property
    def data(self):
        addr = ctypes.addressof(self)
        return (ctypes.c_ubyte * self.len).from_address(addr+self._extra_end)

    def as_bytearray(self):
        return bytearray((ctypes.c_ubyte * ctypes.sizeof(self)).from_address(ctypes.addressof(self)))

    def crc_calculate(self):
        raw_bytes = self.as_bytearray()
        bytes_before = raw_bytes[0:self.__class__.crc8.offset]
        bytes_after = raw_bytes[self.__class__.crc8.offset+1:]

        crc = crcmod.predefined.Crc('crc-8')
        crc.update(bytes_before)
        crc.update(bytes_after)
        return crc.crcValue

    def crc_check(self):
        return self.crc8 == self.crc_calculate()

    def crc_update(self):
        self.crc8 = self.crc_calculate()
        assert self.crc_check()


class Atom(DynamicLengthStructure):
    TYPE = 0xff
    _fields_ = [
        ("type",    ctypes.c_uint8),
        ("_len",    ctypes.c_uint8),
        ("_data",   ctypes.c_ubyte * 0),
    ]

    def __repr__(self):
        r"""
        >>> repr(Atom(0xff, 0))
        "Atom(b'\\xff\\x00')"
        >>> a = Atom(0xfe)
        >>> a.len = 2
        >>> a.data[:] = [0x1, 0x2]
        >>> repr(a)
        "Atom(b'\\xfe\\x02\\x01\\x02')"
        """
        return "%s(%s)" % (self.__class__.__name__, repr(self.as_bytearray())[10:-1])

assert ctypes.sizeof(Atom) == 2


class AtomFormatString(Atom):
    FORMAT = 0x00
    TYPES = {}

    @classmethod
    def create(cls, s):
        u"""
        >>> a1 = AtomFormatString.create("numato")
        >>> a1.len
        6
        >>> a1.str
        'numato'
        >>> a1.as_bytearray()
        bytearray(b'\\xff\\x06numato')
        >>> a1.data[:]
        [110, 117, 109, 97, 116, 111]
        >>> a2 = AtomFormatString.create(u"\u2603")
        >>> a2.len
        3
        >>> a2.str
        '☃'
        >>> a2.data[:]
        [226, 152, 131]
        """
        o = cls(type=cls.TYPE)
        assert o.type == cls.TYPE
        assert o._len == 0
        o.str = s
        return o

    @property
    def str(self):
        return bytearray(self.data[:]).decode('utf-8')

    @str.setter
    def str(self, s):
        b = s.encode('utf-8')
        self.len = len(b)
        self.data[:] = b[:]

    def __repr__(self):
        r"""
        >>> a1 = AtomFormatString.create("numato")
        >>> repr(a1)
        "AtomFormatString('numato')"
        >>> a2 = AtomFormatString.create(u"\u2603")
        >>> repr(a2)
        "AtomFormatString('☃')"
        """
        return u"%s(%r)" % (self.__class__.__name__, self.str)


class AtomFormatURL(AtomFormatString):
    FORMAT = 0x10
    TYPES = {}

    @classmethod
    def create(cls, url):
        u"""
        >>> a1 = AtomFormatURL.create("https://numato")
        >>> a1.len
        6
        >>> a1.url
        'https://numato'
        >>> a1.as_bytearray()
        bytearray(b'\\xff\\x06numato')
        >>> a1.data[:]
        [110, 117, 109, 97, 116, 111]
        >>> a2 = AtomFormatURL.create(u"http://\u2603")
        >>> a2.len
        3
        >>> a2.url
        'https://☃'
        >>> a2.data[:]
        [226, 152, 131]
        """
        o = cls(type=cls.TYPE)
        assert o.type == cls.TYPE
        assert o._len == 0
        o.url = url
        return o

    @property
    def url(self):
        return "https://" + self.str

    @url.setter
    def url(self, url):
        if "://" in url:
            url = url.split("://", 1)[-1]
        self.str = url

    def __repr__(self):
        r"""
        >>> a1 = AtomFormatURL.create("numato")
        >>> repr(a1)
        "AtomFormatURL('https://numato')"
        >>> a2 = AtomFormatURL.create(u"\u2603")
        >>> repr(a2)
        "AtomFormatURL('https://☃')"
        """
        return u"%s(%r)" % (self.__class__.__name__, self.url)


class AtomFormatRelativeURL(AtomFormatString):
    FORMAT = 0x20
    TYPES = {}

    _fields_ = [
        ("index", ctypes.c_uint8),
        ("_data", ctypes.c_char * 0),
    ]

    rurl = AtomFormatString.str

    @classmethod
    def create(cls, index, url):
        u"""
        >>> a1 = AtomFormatRelativeURL.create(2, "numato")
        >>> a1.len
        6
        >>> a1.str
        'numato'
        >>> a1.as_bytearray()
        bytearray(b'\\xff\\x07\\x02numato')
        >>> a1.data[:]
        [110, 117, 109, 97, 116, 111]
        >>> a2 = AtomFormatRelativeURL.create(4, u"\u2603")
        >>> a2.len
        3
        >>> a2.str
        '☃'
        >>> a2.data[:]
        [226, 152, 131]
        >>> a2.as_bytearray()
        bytearray(b'\\xff\\x04\\x04\\xe2\\x98\\x83')
        """
        assert not url.startswith('/')
        o = cls(type=cls.TYPE)
        assert o.type == cls.TYPE
        assert o._len == 1
        o.index = index
        o.str = url
        o._relative_atom = None
        return o

    def __repr__(self):
        r"""
        >>> a1 = AtomFormatRelativeURL.create(1, "numato")
        >>> repr(a1)
        "AtomFormatRelativeURL(1, 'numato')"
        >>> a2 = AtomFormatRelativeURL.create(2, u"\u2603")
        >>> repr(a2)
        "AtomFormatRelativeURL(2, '☃')"
        >>> ar = AtomFormatURL.create("a")
        >>> a3 = AtomFormatRelativeURL.create(2, "b")
        >>> a3._relative_atom = ar
        >>> repr(a3)
        "AtomFormatRelativeURL('https://a/b')"
        """
        if self._relative_atom:
            assert isinstance(self._relative_atom, AtomFormatURL)
            return u"%s('%s/%s')" % (self.__class__.__name__, self._relative_atom.url, self.str)
        else:
            return u"%s(%i, '%s')" % (self.__class__.__name__, self.index, self.str)


class AtomFormatExpandInt(Atom):

    @classmethod
    def create(cls, v):
        r"""
        >>> a1 = AtomFormatExpandInt.create(0)
        >>> a1.len
        0
        >>> a1.v
        0
        >>> a1.as_bytearray()
        bytearray(b'\xff\x00')
        >>> a1 = AtomFormatExpandInt.create(2)
        >>> a1.len
        1
        >>> a1.v
        2
        >>> a1.as_bytearray()
        bytearray(b'\xff\x01\x02')
        >>> a2 = AtomFormatExpandInt.create(2**63)
        >>> a2.len
        8
        >>> a2.v
        9223372036854775808
        >>> a2.as_bytearray()
        bytearray(b'\xff\x08\x00\x00\x00\x00\x00\x00\x00\x80')
        """
        o = cls(type=cls.TYPE)
        assert o.type == cls.TYPE
        assert o._len == 0
        o.v = v
        return o
    
    @property
    def v(self):
        v = 0
        for i, b in enumerate(self.data):
            v |= b << i * 8
        return v

    @v.setter
    def v(self, v):
        b = []
        while v > 0:
            b.append(v & 0xff)
            v = v >> 8

        self.len = len(b)
        self.data[:] = bytearray(b)

    def __repr__(self):
        r"""
        >>> a1 = AtomFormatExpandInt.create(2)
        >>> repr(a1)
        'AtomFormatExpandInt(2)'
        >>> a2 = AtomFormatExpandInt.create(2**63)
        >>> repr(a2)
        'AtomFormatExpandInt(9223372036854775808)'
        """
        return "%s(%i)" % (self.__class__.__name__, self.v)


class AtomFormatTimestamp(AtomFormatExpandInt):
    FORMAT = 0x30
    TYPES = {}

    EPOCH = 1420070400 # 2015/01/01 @ 12:00am (UTC)

    @classmethod
    def create(cls, ts):
        r"""
        >>> t1 = 1421070400.0 # 2015-01-12 13:46:40 UTC
        >>> a1 = AtomFormatTimestamp.create(t1)
        >>> a1._len
        3
        >>> a1.ts
        1421070400
        >>> a1.as_bytearray()
        bytearray(b'\xff\x03@B\x0f')

        >>> t2 = 1451606400.0 # 2016-01-01 00:00:00 UTC
        >>> a2 = AtomFormatTimestamp.create(t2)
        >>> a2._len
        4
        >>> a2.ts
        1451606400
        >>> a2.as_bytearray()
        bytearray(b'\xff\x04\x803\xe1\x01')

        >>> t3 = 1606780801.0 # 2020-01-12 00:00:01 UTC
        >>> a3 = AtomFormatTimestamp.create(t3)
        >>> a3._len
        4
        >>> a3.ts
        1606780801
        >>> a3.as_bytearray()
        bytearray(b'\xff\x04\x81\xf9 \x0b')

        >>> a4 = AtomFormatTimestamp.create(2**63)
        >>> a4._len
        8
        >>> a4.ts
        9223372036854775808
        >>> a4.as_bytearray()
        bytearray(b'\xff\x08\x00r[\xab\xff\xff\xff\x7f')
        """
        o = cls(type=cls.TYPE)
        assert o.type == cls.TYPE
        o.ts = int(round(ts))
        return o

    @property
    def ts(self):
        return self.EPOCH + self.v

    @ts.setter
    def ts(self, ts):
        assert (ts - self.EPOCH) > 0, (ts - self.EPOCH)
        self.v = ts - self.EPOCH
        
    def __repr__(self):
        r"""
        >>> a1 = AtomFormatTimestamp.create(1421070400)
        >>> repr(a1)
        'AtomFormatTimestamp(1421070400)'
        >>> a2 = AtomFormatTimestamp.create(2**63)
        >>> repr(a2)
        'AtomFormatTimestamp(9223372036854775808)'
        """
        return u"%s(%i)" % (self.__class__.__name__, self.ts)



def _l(license, version):
    return license << 3 | version

class _NamesStruct(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("license", ctypes.c_uint8, 5),
        ("version", ctypes.c_uint8, 3),
    ]
class _NamesUnion(ctypes.LittleEndianUnion):
    _pack_ = 1
    _fields_ = [
        ("_value", ctypes.c_uint8),
        ("_parts", _NamesStruct)
    ]

class AtomFormatLicense(Atom):
    FORMAT = 0x40
    TYPES = {}

    @enum.unique
    class Names(enum.IntEnum):

        Invalid         = 0
        # -
        MIT             = _l(1, 1)
        # -
        BSD_simple      = _l(2, 1)
        BSD_new         = _l(2, 2)
        BSD_isc         = _l(2, 3)
        # -
        Apache_v2       = _l(3, 1)
        # -
        GPL_v2          = _l(4, 1)
        GPL_v3          = _l(4, 2)
        # -
        LGPL_v21        = _l(5, 1)
        LGPL_v3         = _l(5, 2)
        # -
        CC0_v1          = _l(6, 1)
        # -
        CC_BY_v10       = _l(7, 1)
        CC_BY_v20       = _l(7, 2)
        CC_BY_v25       = _l(7, 3)
        CC_BY_v30       = _l(7, 4)
        CC_BY_v40       = _l(7, 5)
        # -
        CC_BY_SA_v10    = _l(8, 1)
        CC_BY_SA_v20    = _l(8, 2)
        CC_BY_SA_v25    = _l(8, 3)
        CC_BY_SA_v30    = _l(8, 4)
        CC_BY_SA_v40    = _l(8, 5)
        # -
        TAPR_v10        = _l(9, 1) 
        # -
        CERN_v11        = _l(10, 1) 
        CERN_v12        = _l(10, 2) 
        # -
        Proprietary     = 0xff

    _anonymous_ = ("_license",)
    _fields_ = [
        ("_license", _NamesUnion),
        ("_data", ctypes.c_char * 0),
    ]

    @classmethod
    def create(cls, value):
        r"""
        >>> a1 = AtomFormatLicense.create(AtomFormatLicense.Names.GPL_v2)
        >>> a1._len
        1
        >>> a1.license
        'GPL'
        >>> a1.version
        2
        >>> a1.as_bytearray()
        bytearray(b'\xff\x01!')
        >>> a2 = AtomFormatLicense.create(AtomFormatLicense.Names.CC_BY_SA_v30)
        >>> a2._len
        1
        >>> a2.license
        'CC BY SA'
        >>> a2.version
        3.0
        >>> a2.as_bytearray()
        bytearray(b'\xff\x01D')
        """
        o = cls(type=cls.TYPE)
        assert o.type == cls.TYPE
        assert o._len == 1
        o.value = value
        return o

    @property
    def value(self):
        return self.Names(self._value)

    @value.setter
    def value(self, license):
        assert isinstance(license, self.Names), repr(license)
        self._value = license.value
        
    @property
    def license(self):
        return " ".join(self.value.name.split('_')[:-1])

    @property
    def version(self):
        vstr = self.value.name.rsplit('_')[-1]
        if not vstr.startswith('v'):
            return vstr
        
        if len(vstr) == 2:
            return int(vstr[1])
        elif len(vstr) == 3:
            return int(vstr[1]) + (int(vstr[2])/10.0)

        assert False, "Invalid version %r" % vstr

    def __repr__(self):
        r"""
        >>> a1 = AtomFormatLicense.create(AtomFormatLicense.Names.GPL_v2)
        >>> repr(a1)
        'AtomFormatLicense(GPL, 2)'
        >>> a2 = AtomFormatLicense.create(AtomFormatLicense.Names.CC_BY_SA_v30)
        >>> repr(a2)
        'AtomFormatLicense(CC BY SA, 3.0)'
        """
        return u"%s(%s, %s)" % (self.__class__.__name__, self.license, self.version)


class AtomFormatSizeOffset(Atom):
    FORMAT = 0x50
    TYPES = {}

    class Small(ctypes.LittleEndianStructure):
        _pack_ = 1
        _fields_ = [
            ("offset", ctypes.c_uint8),
            ("size", ctypes.c_uint8),
        ]

    class Medium(ctypes.LittleEndianStructure):
        _pack_ = 1
        _fields_ = [
            ("offset", ctypes.c_uint16),
            ("size", ctypes.c_uint16),
        ]

    class Large(ctypes.LittleEndianStructure):
        _pack_ = 1
        _fields_ = [
            ("offset", ctypes.c_uint32),
            ("size", ctypes.c_uint32),
        ]

    _fields_ = [
        ("_data", ctypes.c_ubyte * 0),
    ]


    @classmethod
    def create(cls, offset, size):
        r"""
        >>> e = AtomFormatSizeOffset.create(5, 10)
        >>> e.len
        2
        >>> e.offset
        5
        >>> e.size
        10
        >>> e.as_bytearray()
        bytearray(b'\xff\x02\x05\n')

        >>> e = AtomFormatSizeOffset.create(700, 10)
        >>> e.len
        4
        >>> e.offset
        700
        >>> e.size
        10
        >>> e.as_bytearray()
        bytearray(b'\xff\x04\xbc\x02\n\x00')
        """
        if offset < 2**8 and size < 2**8:
            struct = AtomFormatSizeOffset.Small
        elif offset < 2**16 and size < 2**16:
            struct = AtomFormatSizeOffset.Medium
        elif offset < 2**32 and size < 2**32:
            struct = AtomFormatSizeOffset.Large
        else:
            assert False

        o = cls(type=cls.TYPE)
        o.len = ctypes.sizeof(struct)
        o.offset = offset
        o.size = size
        return o

    @property
    def _data_struct(self):
        if self.len == ctypes.sizeof(AtomFormatSizeOffset.Small):
            return AtomFormatSizeOffset.Small.from_address(ctypes.addressof(self.data))
        elif self.len == ctypes.sizeof(AtomFormatSizeOffset.Medium):
            return AtomFormatSizeOffset.Medium.from_address(ctypes.addressof(self.data))
        elif self.len == ctypes.sizeof(AtomFormatSizeOffset.Large):
            return AtomFormatSizeOffset.Large.from_address(ctypes.addressof(self.data))
        else:
            assert False

    @property
    def offset(self):
        return self._data_struct.offset

    @offset.setter
    def offset(self, value):
        self._data_struct.offset = value

    @property
    def size(self):
        return self._data_struct.size

    @size.setter
    def size(self, value):
        self._data_struct.size = value

    def __repr__(self):
        r"""
        >>> a1 = AtomFormatSizeOffset.create(1, 2)
        >>> repr(a1)
        'AtomFormatSizeOffset(1, 2)'
        >>> a2 = AtomFormatSizeOffset.create(2**31, 2)
        >>> repr(a2)
        'AtomFormatSizeOffset(2147483648, 2)'
        """
        return u"%s(%i, %i)" % (self.__class__.__name__, self.offset, self.size)

# Actual atoms
ATOMS = [
    # Product Identification atoms
    ("Designer ID",               AtomFormatURL),
    ("Manufacturer ID",           AtomFormatURL),
    ("Product ID",                AtomFormatURL),
    ("Product Version",           AtomFormatString),
    ("Product Serial",            AtomFormatString),
    ("Product Part Number",       AtomFormatString),
    # Auxiliary atoms
    ("Auxiliary URL",             AtomFormatURL),
    # 0x2_ - PCB information atoms
    ("PCB Repository",            AtomFormatRelativeURL),
    ("PCB Revision",              AtomFormatString),
    ("PCB License",               AtomFormatLicense),
    ("PCB Production Batch ID",   AtomFormatTimestamp),
    ("PCB Population Batch ID",   AtomFormatTimestamp),
    # 0x3_ - Firmware atoms
    ("Firmware Description",      AtomFormatString),
    ("Firmware Repository",       AtomFormatRelativeURL),
    ("Firmware Revision",         AtomFormatString),
    ("Firmware License",          AtomFormatLicense),
    ("Firmware Program Date",     AtomFormatTimestamp),
    # 0x4_ - EEPROM atoms
    ("EEPROM Total Size",         AtomFormatSizeOffset),
    ("EEPROM Vendor Data",        AtomFormatSizeOffset),
    ("EEPROM TOFE Data",          AtomFormatSizeOffset),
    ("EEPROM User Data",          AtomFormatSizeOffset),
    ("EEPROM GUID",               AtomFormatSizeOffset),
    ("EEPROM Hole",               AtomFormatSizeOffset),
    ("EEPROM Part Number",        AtomFormatString),
    # 0x5_ - Other information links
    ("Sample Code Repository",    AtomFormatRelativeURL),
    ("Documentation Site",        AtomFormatRelativeURL),
]

ATOMS_TYPES = {}
for i, (name, atom_format_cls) in enumerate(ATOMS):
    atom_i = len(atom_format_cls.TYPES)+1
    atom_type = atom_format_cls.FORMAT | atom_i
    assert atom_type not in ATOMS_TYPES
    exec("""
class Atom%(name)s(%(format)s):
    ORDER = %(i)i
    TYPE = %(atom_type)s

ATOMS_TYPES[%(atom_type)s] = Atom%(name)s
%(format)s.TYPES[%(atom_i)s] = Atom%(name)s
""" % {
        "i": i,
        "name": "".join(name.split()),
        "format": atom_format_cls.__name__,
        "atom_i": hex(atom_i),
        "atom_type": hex(atom_type),
    })


class AtomCommon(DynamicLengthStructure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_char * 5),
        ("version", ctypes.c_uint8),
        ("atoms", ctypes.c_uint8),
        ("crc8", ctypes.c_ubyte),
        ("_len", ctypes.c_uint32),
        ("_data", ctypes.c_ubyte * 0),
    ]

    MAGIC = b'\x00\x01\x02\x03\x04'
    RAGIC = b'\0x4\0x3\0x2\x01\x00'

    def __init__(self):
        super().__init__()
        self.populate()

    def populate(self):
        self.magic = self.MAGIC
        self.version = 0x1
        self.atoms = 0
        self.len = len(self.RAGIC)
        self.data[:] = self.RAGIC[:]
        self.crc_update()

    def add_atom(self, atom):
        assert bytes(self.ragic) == self.RAGIC

        if self.atoms > 0:
            assert atom.ORDER >= self.get_atom(self.atoms-1).ORDER

        if isinstance(atom, AtomFormatRelativeURL):
            assert atom.index < self.atoms, "%i < %i" % (atom.index, self.atoms)

        atom_size = ctypes.sizeof(atom)

        atom_offset = self.len - len(self.RAGIC)
        self.atoms += 1

        self.len += atom_size
        ctypes.memmove(ctypes.addressof(self.data)+atom_offset, ctypes.addressof(atom), atom_size)
        self.data[self.len - len(self.RAGIC):] = self.RAGIC[:]
        self.crc_update()

    def get_atom(self, v):
        assert v < self.atoms, "%i < %i" % (v, self.atoms)
        current_offset = 0
        a = None
        for i in range(0, v+1):
            a = Atom.from_address(ctypes.addressof(self._data)+current_offset)
            current_offset += ctypes.sizeof(Atom)
            current_offset += a._len
        assert a is not None, a
        assert a.type in ATOMS_TYPES
        a = ATOMS_TYPES[a.type].from_address(ctypes.addressof(a))

        if isinstance(a, AtomFormatRelativeURL):
            assert a.index != i, "%i != %i" % (a.index, i)
            a._relative_atom = self.get_atom(a.index)

        return a

    def __repr__(self):
        s = self.__class__.__name__ + "\n"
        s += print_struct(self) + "\n"
        s += "atoms (%i, %i bytes):\n" % (self.atoms, self.len - len(self.RAGIC))
        for i in range(0, self.atoms):
            s += "    (%i, %r)\n" % (i, self.get_atom(i))
        s += "ragic: %s\n" % self.ragic
        return s[:-1]

    @property
    def ragic(self):
        return bytearray(self.data[self.len - len(self.RAGIC):])


class TOFEAtoms(AtomCommon):
    """Structure representing the TOFE EEPROM format."""
    MAGIC = b'TOFE\0'
    RAGIC = MAGIC[::-1]


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    for atom_type_cls in sorted(ATOMS_TYPES.values(), key=lambda x: x.ORDER):
        print("  ", "0x%02x" % atom_type_cls.TYPE, atom_type_cls.__name__)

    print("====")
    test = TOFEAtoms()
    b = test.as_bytearray()
    print(len(b), b)
    print(repr(test))
    print("----")
    test.add_atom(AtomManufacturerID.create("numato.com"))
    b = test.as_bytearray()
    print(len(b), b)
    print(repr(test))
    print("----")
    test.add_atom(AtomProductID.create("opsis.h2u.tv"))
    b = test.as_bytearray()
    print(len(b), b)
    print(repr(test))
    print("----")
    test.add_atom(AtomPCBRepository.create(1, "r/pcb.git"))
    b = test.as_bytearray()
    print(len(b), b)
    print(repr(test))
    print("====")

    import time

    # Testing MilkyMist EEPROM
    # ------------------------------------------------
    milkymist_eeprom = TOFEAtoms()
    milkymist_eeprom.add_atom(AtomManufacturerID.create("numato.com"))
    milkymist_eeprom.add_atom(AtomProductID.create("tofe.io/milkymist"))
    milkymist_eeprom.add_atom(AtomPCBRepository.create(1, "r/pcb.git"))
    milkymist_eeprom.add_atom(AtomPCBRevision.create("aaaaaaa"))
    milkymist_eeprom.add_atom(AtomPCBLicense.create(AtomPCBLicense.Names.CC_BY_SA_v40))
    milkymist_eeprom.add_atom(AtomPCBProductionBatchID.create(time.time()))
    milkymist_eeprom.add_atom(AtomPCBPopulationBatchID.create(time.time()))
    milkymist_eeprom.add_atom(AtomEEPROMTotalSize.create(0, 128))
    milkymist_eeprom.add_atom(AtomEEPROMPartNumber.create("24LC01BT-1/OT"))

    b = milkymist_eeprom.as_bytearray()
    print("-"*10)
    print("MilkyMist")
    print(len(b), b)
    print(repr(milkymist_eeprom))

    # LowSpeedIO EEPROM
    # ------------------------------------------------
    lowspeedio_eeprom = TOFEAtoms()
    lowspeedio_eeprom.add_atom(AtomManufacturerID.create("numato.com"))
    lowspeedio_eeprom.add_atom(AtomProductID.create("tofe.io/lowspeedio"))

    b = lowspeedio_eeprom.as_bytearray()
    print("-"*10)
    print("LowSpeedIO")
    print(len(b), b)
    print(repr(lowspeedio_eeprom))
