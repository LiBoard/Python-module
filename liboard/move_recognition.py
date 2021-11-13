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

from abc import ABC, abstractmethod

from chess import Board, Move
from bitstring import Bits
from chess import Board
from typing import Optional, Callable, Any
from time import time_ns


class MoveRecognizer(ABC):
    # region Properties
    @property
    @abstractmethod
    def board(self) -> Board:
        pass

    @property
    @abstractmethod
    def move_delay(self) -> int:
        pass

    # endregion

    @abstractmethod
    def new_board_data(self, bits: Bits):
        pass

    @abstractmethod
    def tick(self):
        pass

    def find_move(self, appearances: set, disappearances: set, temp_lifted: set) -> Optional[Move]:
        if len(disappearances) == 1 and len(appearances) == 1:  # "normal" move
            move = self._find_candidate_move(
                disappearances.pop(), appearances.pop())
            if move and not self.board.is_capture(move) and not self.board.is_castling(move):
                return move
        elif len(disappearances) == 1 and not appearances and temp_lifted:  # "simple" capture
            from_square = disappearances.pop()
            for tlp in temp_lifted:
                move = self._find_candidate_move(from_square, tlp)
                if move and self.board.is_capture(move):
                    return move
        elif len(disappearances) == 2 and len(appearances) == 1:  # en passant
            to_square = appearances.pop()
            for from_square in disappearances:
                move = self._find_candidate_move(from_square, to_square)
                if move and self.board.is_en_passant(move):
                    return move
        elif len(disappearances) == 2 and len(appearances) == 2:  # castling
            for from_square in disappearances:
                for to_square in appearances:
                    move = self._find_candidate_move(from_square, to_square)
                    if move and self.board.is_castling(move):
                        return move

    def _find_candidate_move(self, from_square: int, to_square: int) -> Optional[Move]:
        """
        Find a legal move from from_square to to_square.
        :param from_square: The starting square for the move.
        :param to_square: The target square for the move.
        :return: The Move if one was found. Otherwise return None.
        """
        try:
            return self.board.find_move(from_square, to_square)
        except ValueError:
            return None


class DoubleSidedMoveRecognizer(MoveRecognizer):
    def __init__(self, move_delay=0):
        self._board = Board()
        self._move_delay = move_delay

        self._physical_pos = _STARTING_POSITION
        self._physical_pos_timestamp = 0
        self._pos_checked = False
        self._lifted = set()

        self._start_handler: Optional[Callable[[Board], Any]] = None
        self._move_handler: Optional[Callable[[Board, Move], Any]] = None

    # region Properties
    @property
    def move_delay(self) -> int:
        return self._move_delay

    @property
    def board(self) -> Board:
        return self._board

    # endregion

    # region Handler decorators
    def start_handler(self, handler: Callable[[Board], bool]):
        """Set the handler for game starts."""
        self._start_handler = handler
        return handler

    def move_handler(self, handler: Callable[[Board, Move], bool]):
        """Set the handler for new moves."""
        self._move_handler = handler
        return handler

    # endregion

    def start_game(self):
        self.board.reset()
        self._lifted.clear()
        if self._start_handler is not None:
            self._start_handler(self.board)

    def new_board_data(self, bits: Bits):
        self._physical_pos = _Position(bits)
        if self._physical_pos == _STARTING_POSITION:
            return self.start_game()
        self._physical_pos_timestamp = time_ns()
        self._pos_checked = False
        self._lifted += _Position(self.board).occupied_squares - \
            self._physical_pos.occupied_squares

    def tick(self):
        if not self._pos_checked and time_ns() >= (
                self._physical_pos_timestamp + self.move_delay) and self._physical_pos != _Position(self.board):
            self._pos_checked = True
            appearances = self._physical_pos.occupied_squares - \
                _Position(self.board).occupied_squares
            disappearances = _Position(
                self.board).occupied_squares - self._physical_pos.occupied_squares
            temp_lifted = self._lifted & self._physical_pos.occupied_squares
            move = self.find_move(appearances, disappearances, temp_lifted)
            if move:
                self.board.push(move)
                self._lifted.clear()
                if self._move_handler is not None:
                    self._move_handler(self.board, move)


class _Position:
    def __init__(self, *args):
        if len(args) != 1:
            raise IndexError
        if type(args[0]) == Bits:
            self.bits = args[0]
        elif type(args[0]) == Board:
            self.bits = Bits(uint=args[0].occupied, length=64)
        else:
            raise TypeError
        self.occupied_squares = {63 - i for i in self.bits.findall('0b1')}

    def __eq__(self, other):
        if isinstance(other, _Position):
            return other.bits == self.bits
        return super.__eq__(self, other)


_STARTING_POSITION = _Position(Bits(hex='FFFF00000000FFFF'))
