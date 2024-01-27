"""A module for managing the terminal state and output."""
import random
import shutil
import sys
import time
import argparse
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import ansitools, motion


@dataclass
class OutputArea:
    """A class for storing the output area of an effect.

    Args:
        top (int): top row of the output area
        right (int): right column of the output area
        bottom (int): bottom row of the output area. Defaults to 1.
        left (int): left column of the output area. Defaults to 1.

    """

    top: int
    right: int
    bottom: int = 1
    left: int = 1

    def __post_init__(self):
        self.center_row = max(self.top // 2, 1)
        self.center_column = max(self.right // 2, 1)
        self.center = motion.Coord(self.center_column, self.center_row)

    def coord_in_output_area(self, coord: motion.Coord) -> bool:
        """Checks whether a coordinate is within the output area.

        Args:
            coord (motion.Coord): coordinate to check

        Returns:
            bool: whether the coordinate is within the output area
        """
        return self.left <= coord.column <= self.right and self.bottom <= coord.row <= self.top


class Terminal:
    """A class for managing the terminal state and output."""

    class CharacterSort(Enum):
        """An enum for sorting characters by column, row, or diagonal."""

        COLUMN_LEFT_TO_RIGHT = auto()
        COLUMN_RIGHT_TO_LEFT = auto()
        ROW_TOP_TO_BOTTOM = auto()
        ROW_BOTTOM_TO_TOP = auto()
        DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT = auto()
        DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT = auto()
        DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT = auto()
        DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT = auto()

    def __init__(self, input_data: str, args: argparse.Namespace):
        self.input_data = input_data
        self.args = args
        self.width, self.height = self._get_terminal_dimensions()
        self.characters = self._decompose_input(args.xterm_colors, args.no_color)
        self.non_input_characters: list[EffectCharacter] = []
        self.input_width = max([character.input_coord.column for character in self.characters])
        self.input_height = max([character.input_coord.row for character in self.characters])
        self.output_area = OutputArea(min(self.height - 1, self.input_height), self.input_width)
        self.characters = [
            character
            for character in self.characters
            if character.input_coord.row <= self.output_area.top
            and character.input_coord.column <= self.output_area.right
        ]
        self.character_by_input_coord: dict[tuple[int, int], EffectCharacter] = {
            (character.input_coord.row, character.input_coord.column): character for character in self.characters
        }
        self.animation_rate = args.animation_rate
        self.last_time_printed = time.time()
        self._update_terminal_state()

        self._prep_outputarea()

    def _get_terminal_dimensions(self) -> tuple[int, int]:
        """Gets the terminal dimensions.

        Returns:
            tuple[int, int]: terminal width and height
        """
        try:
            terminal_width, terminal_height = shutil.get_terminal_size()
        except OSError:
            # If the terminal size cannot be determined, return default values
            return 80, 24
        return terminal_width, terminal_height

    @staticmethod
    def get_piped_input() -> str:
        """Gets the piped input from stdin.

        Returns:
            str: string from stdin
        """
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            return input_data
        else:
            return ""

    def _decompose_input(self, use_xterm_colors: bool, no_color: bool) -> list[EffectCharacter]:
        """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
        relative to the input display location.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
        above the cursor.

        Args:
            use_xterm_colors (bool): whether to convert colors to the closest XTerm-256 color

        Returns:
            list[Character]: list of EffectCharacter objects
        """
        # handle whitespace characters
        self.input_data = self.input_data.replace("\t", " " * self.args.tab_width)
        formatted_lines = []
        if not self.input_data.strip():
            self.input_data = "No Input."
        input_lines = self.input_data.splitlines()
        if not self.args.no_wrap:
            for line in input_lines:
                while len(line) > self.width:
                    formatted_lines.append(line[: self.width])
                    line = line[self.width :]
                formatted_lines.append(line)
        else:
            for line in input_lines:
                formatted_lines.append(line[: self.width])
        input_height = len(formatted_lines)
        input_characters = []
        for row, line in enumerate(formatted_lines):
            for column, symbol in enumerate(line):
                if symbol != " ":
                    character = EffectCharacter(symbol, column + 1, input_height - row)
                    character.animation.use_xterm_colors = use_xterm_colors
                    character.animation.no_color = no_color
                    input_characters.append(character)
        return input_characters

    def _update_terminal_state(self):
        """Update the internal representation of the terminal state with the current position
        of all active characters.
        """
        rows = [[" " for _ in range(self.output_area.right)] for _ in range(self.output_area.top)]
        for character in sorted(self.characters + self.non_input_characters, key=lambda c: c.layer):
            if character.is_active:
                try:
                    # do not allow characters to wrap around the terminal via negative coordinates
                    if character.motion.current_coord.row <= 0 or character.motion.current_coord.column <= 0:
                        continue
                    rows[character.motion.current_coord.row - 1][
                        character.motion.current_coord.column - 1
                    ] = character.symbol
                except IndexError:
                    # ignore characters that are outside the output area
                    pass
        terminal_state = ["".join(row) for row in rows]
        self.terminal_state = terminal_state

    def _prep_outputarea(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        sys.stdout.write(ansitools.HIDE_CURSOR())
        print("\n" * self.output_area.top)

    def random_column(self) -> int:
        """Get a random column position. Position is within the output area.

        Returns:
            int: a random column position (1 <= x <= output_area.right)"""
        return random.randint(1, self.output_area.right)

    def random_row(self) -> int:
        """Get a random row position. Position is within the output area.

        Returns:
            int: a random row position (1 <= x <= terminal.output_area.top)"""
        return random.randint(1, self.output_area.top)

    def random_coord(self, outside_scope=False) -> motion.Coord:
        """Get a random coordinate. Coordinate is within the output area unless outside_scope is True.

        Args:
            outside_scope (bool, optional): whether the coordinate should fall outside the output area. Defaults to False.

        Returns:
            motion.Coord: a random coordinate . Coordinate is within the output area unless outside_scope is True."""
        if outside_scope is True:
            random_coord_above = motion.Coord(self.random_column(), self.output_area.top + 1)
            random_coord_below = motion.Coord(self.random_column(), -1)
            random_coord_left = motion.Coord(-1, self.random_row())
            random_coord_right = motion.Coord(self.output_area.right + 1, self.random_row())
            return random.choice([random_coord_above, random_coord_below, random_coord_left, random_coord_right])
        else:
            return motion.Coord(self.random_column(), self.random_row())

    def add_character(self, symbol: str) -> EffectCharacter:
        """Adds a character to the terminal for printing. Used to create characters that are not in the input data.
        Characters added with this method will have input coordinates outside the output area (0,0).

        Args:
            symbol (str): symbol to add

        Returns:
            EffectCharacter: the character that was added
        """
        character = EffectCharacter(symbol, 0, 0)
        self.non_input_characters.append(character)
        return character

    def get_input_by_row(self) -> dict[int, list[EffectCharacter]]:
        """Get a dict of rows of EffectCharacters where the key is the input row index. 0 is the bottom row.

        Returns:
            dict[int,list[EffectCharacter]]: dict of rows of EffectCharacters where the key is the row index. 0 is the bottom row.
        """
        rows: dict[int, list[EffectCharacter]] = dict()
        for row_index in range(self.output_area.top + 1):
            characters_in_row = [character for character in self.characters if character.input_coord.row == row_index]
            if characters_in_row:
                rows[row_index] = characters_in_row
        return rows

    def get_input_by_column(self) -> dict[int, list[EffectCharacter]]:
        """Get a dict columns of EffectCharacters where the key is the input column index. 0 is the left column.

        Returns:
            dict[int,list[EffectCharacter]]: dict of columns of EffectCharacters where the key is the column index. 0 is the left column.
        """
        columns: dict[int, list[EffectCharacter]] = dict()
        for column_index in range(self.output_area.right + 1):
            characters_in_column = [
                character for character in self.characters if character.input_coord.column == column_index
            ]
            if characters_in_column:
                columns[column_index] = characters_in_column
        return columns

    def get_characters(
        self, sort_order: CharacterSort = CharacterSort.ROW_TOP_TO_BOTTOM
    ) -> list[list[EffectCharacter]]:
        """Get a list of all EffectCharacters in the terminal sorted by the specified sort_order.

        Args:
            sort_order (CharacterSort, optional): order to sort the characters. Defaults to ROW_TOP_TO_BOTTOM.

        Returns:
            list[list[EffectCharacter]]: list of lists of EffectCharacters in the terminal. Inner lists correspond to rows,
            columns, or diagonals depending on the sort_order.
        """
        if sort_order in (self.CharacterSort.COLUMN_LEFT_TO_RIGHT, self.CharacterSort.COLUMN_RIGHT_TO_LEFT):
            columns = []
            for column_index in range(self.output_area.right + 1):
                characters_in_column = [
                    character for character in self.characters if character.input_coord.column == column_index
                ]
                if characters_in_column:
                    columns.append(characters_in_column)
            if sort_order == self.CharacterSort.COLUMN_RIGHT_TO_LEFT:
                columns.reverse()
            return columns

        elif sort_order in (self.CharacterSort.ROW_BOTTOM_TO_TOP, self.CharacterSort.ROW_TOP_TO_BOTTOM):
            rows = []
            for row_index in range(self.output_area.top + 1):
                characters_in_row = [
                    character for character in self.characters if character.input_coord.row == row_index
                ]
                if characters_in_row:
                    rows.append(characters_in_row)
            if sort_order == self.CharacterSort.ROW_TOP_TO_BOTTOM:
                rows.reverse()
            return rows
        elif sort_order in (
            self.CharacterSort.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            self.CharacterSort.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
        ):
            diagonals = []
            for diagonal_index in range(self.output_area.top + self.output_area.right + 1):
                characters_in_diagonal = [
                    character
                    for character in self.characters
                    if character.input_coord.row + character.input_coord.column == diagonal_index
                ]
                if characters_in_diagonal:
                    diagonals.append(characters_in_diagonal)
            if sort_order == self.CharacterSort.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT:
                diagonals.reverse()
            return diagonals
        elif sort_order in (
            self.CharacterSort.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            self.CharacterSort.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        ):
            diagonals = []
            for diagonal_index in range(
                self.output_area.left - self.output_area.top, self.output_area.right - self.output_area.bottom + 1
            ):
                characters_in_diagonal = [
                    character
                    for character in self.characters
                    if character.input_coord.column - character.input_coord.row == diagonal_index
                ]
                if characters_in_diagonal:
                    diagonals.append(characters_in_diagonal)
            if sort_order == self.CharacterSort.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT:
                diagonals.reverse()
            return diagonals
        else:
            raise ValueError(f"Invalid sort_order: {sort_order}")

    def get_character_by_input_coord(self, row: int, column: int) -> EffectCharacter:
        """Get an EffectCharacter by its input coordinates.

        Args:
            row (int): row of the character
            column (int): column of the character

        Returns:
            EffectCharacter: the character at the specified coordinates
        """
        return self.character_by_input_coord[(row, column)]

    def print(self):
        """Prints the current terminal state to stdout while preserving the cursor position."""
        self._update_terminal_state()
        time_since_last_print = time.time() - self.last_time_printed
        if time_since_last_print < self.animation_rate:
            time.sleep(self.animation_rate - time_since_last_print)
        output = "\n".join(self.terminal_state[::-1])
        sys.stdout.write(ansitools.DEC_SAVE_CURSOR_POSITION())
        sys.stdout.write(ansitools.MOVE_CURSOR_UP(self.output_area.top))
        sys.stdout.write(ansitools.MOVE_CURSOR_TO_COLUMN(1))
        sys.stdout.write(output)
        sys.stdout.write(ansitools.DEC_RESTORE_CURSOR_POSITION())
        sys.stdout.flush()
        self.last_time_printed = time.time()
