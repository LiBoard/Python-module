#  LiBoard
#  Copyright (C) 2021 Philipp Leclercq
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 3 as published by
#  the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Classes for handling connections to physical boards.
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager

from bitstring import Bits
from serial import Serial
from serial.threaded import Protocol, ReaderThread
from typing import Callable, Any, Optional


class USBBoard:
    def __init__(self, port, baudrate, bitboard_handler: Optional[Callable[[Bits], Any]] = None, configurable=False):
        self._port = port
        self._baudrate = baudrate
        self._configurable = configurable
        self._bitboard_callback = bitboard_handler

    # region Properties
    @property
    def configurable(self):
        return self._configurable

    @property
    def baudrate(self):
        return self._baudrate

    @property
    def port(self):
        return self._port

    # endregion

    @contextmanager
    def connect(self):
        with Serial(self.port, self.baudrate) as serial, ReaderThread(serial, _USBBoardProtocol) as protocol:
            protocol.register_bitboard_handler(self._bitboard_callback)
            yield None


class _USBBoardProtocol(Protocol):
    def __init__(self):
        self._bytes = []
        self._bitboard_handler = None

    def register_bitboard_handler(self, handler: Optional[Callable[[Bits], Any]]):
        self._bitboard_handler = handler

    def data_received(self, data):
        self._bytes += data

        if len(self._bytes) >= 8:
            bitboard = Bits(self._bytes[:8])
            self._bytes = self._bytes[8:]
            if self._bitboard_handler is not None:
                self._bitboard_handler(bitboard)

    def connection_made(self, transport):
        pass

    def connection_lost(self, exc):
        pass
