#
# Copyright (C) 2012-2022 Sébastien Helleu <flashcode@flashtux.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Interactive maze generator and solver for WeeChat.
#
# History:
#
# 2022-02-20, Sébastien Helleu <flashcode@flashtux.org>:
#     version 1.0.0: first public version
# 2012-10-10, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.0.1: initial release
#

"""Maze generator and solver for WeeChat."""

from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Tuple

import random

try:
    import weechat
    IMPORT_OK = True
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    IMPORT_OK = False

SCRIPT_NAME = "maze"
SCRIPT_AUTHOR = "Sébastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "1.0.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Interactive maze generator and solver"

SCRIPT_COMMAND = "maze"

MAZE_KEYS: Dict[str, Tuple[str, str]] = {
    "n": ("", "new maze"),
    "d": ("default", "default size"),
    "+": ("+", "bigger"),
    "-": ("-", "smaller"),
    "s": ("solve", "solve"),
    "i": ("isolve", "solve interactively"),
    "r": ("reset", "reset solution"),
}


@dataclass
class Maze:
    """Maze."""
    width: int = 0
    height: int = 0

    cells: List[int] = field(default_factory=list, init=False)
    solution: List[tuple[int, int, bool]] = field(default_factory=list,
                                                  init=False)
    buffer: str = field(init=False)
    timer: str = field(default="", init=False)

    # cell status
    VISITED: ClassVar[int] = 1        # visited cell
    TOP: ClassVar[int] = 2            # door opened on top
    BOTTOM: ClassVar[int] = 4         # door opened on bottom
    LEFT: ClassVar[int] = 8           # door opened on the left
    RIGHT: ClassVar[int] = 16         # door opened on the right
    SOLUTION: ClassVar[int] = 32      # cell part of the solution
    SOLUTION_INT: ClassVar[int] = 64  # cell displayed for solution

    def __post_init__(self) -> None:
        """Initialize maze with the given size."""
        self.cells = [0] * (self.width * self.height)
        self.cells[0] |= self.LEFT
        self.cells[-1] |= self.RIGHT
        self.solution = []
        self.buffer = Maze.open_buffer()
        if self.buffer:
            keys = ", ".join([
                f"alt+\"{key}\": {value[1]}"
                for key, value in MAZE_KEYS.items()
            ])
            weechat.buffer_set(
                self.buffer,
                "title",
                f"Maze {self.width}x{self.height} | {keys}",
            )

    @staticmethod
    def open_buffer() -> str:
        """Open maze buffer."""
        buf: str = weechat.buffer_search("python", "maze")
        if not buf:
            buf = weechat.buffer_new(
                "maze",
                "maze_input_buffer",
                "",
                "maze_close_buffer",
                "",
            )
        if buf:
            weechat.buffer_set(buf, "type", "free")
            for key, value in MAZE_KEYS.items():
                weechat.buffer_set(
                    buf,
                    f"key_bind_meta-{key}",
                    f"/{SCRIPT_COMMAND} {value[0]}".strip(),
                )
            weechat.buffer_set(buf, "display", "1")
        return buf

    def get_adjacent_cells(
            self, col: int, line: int
    ) -> List[Tuple[int, int, int, int]]:
        """Get adjacent cells."""
        list_cells = []
        if col < self.width - 1:  # right
            list_cells.append((col + 1, line, self.RIGHT, self.LEFT))
        if line < self.height - 1:  # bottom
            list_cells.append((col, line + 1, self.BOTTOM, self.TOP))
        if line > 0:  # top
            list_cells.append((col, line - 1, self.TOP, self.BOTTOM))
        if col > 0:  # left
            list_cells.append((col - 1, line, self.LEFT, self.RIGHT))
        return list_cells

    def generate(self) -> None:
        """Generate a new random maze."""
        if not self.cells:
            return
        col: int = 0
        line: int = 0
        self.cells[0] |= self.VISITED
        stack: List[Tuple[int, int]] = []
        while True:
            pos: int = (line * self.width) + col
            list_cells: List[Tuple[int, int, int, int]] = (
                self.get_adjacent_cells(col, line)
            )
            random.shuffle(list_cells)
            for col2, line2, to_neighbor, from_neighbor in list_cells:
                pos2 = (line2 * self.width) + col2
                # neighbor not visited?
                if not self.cells[pos2] & self.VISITED:
                    # open door from (x, y) to neighbor
                    self.cells[pos] |= to_neighbor
                    # open door from neighbor to (x, y) (reverse)
                    self.cells[pos2] |= from_neighbor | self.VISITED
                    stack.append((col, line))
                    col, line = col2, line2
                    break
            else:
                col, line = stack.pop()
                if not stack:
                    break

    def solve(self, interactive: bool = False) -> None:
        """Solve a maze: find path from entry (0,0) to exit (n,n)."""
        self.remove_timer()
        for index, cell in enumerate(self.cells):
            self.cells[index] = cell & ~(self.VISITED | self.SOLUTION
                                         | self.SOLUTION_INT)
        col: int = 0
        line: int = 0
        self.cells[0] |= self.SOLUTION
        self.solution = [(col, line, True)]
        stack: List[Tuple[int, int]] = []
        visited_solution = self.VISITED | self.SOLUTION
        while not self.cells[-1] & self.SOLUTION:
            pos: int = (line * self.width) + col
            self.cells[pos] |= self.VISITED
            list_cells: List[Tuple[int, int, int, int]] = (
                self.get_adjacent_cells(col, line)
            )
            for col2, line2, to_neighbor, _ in list_cells:
                pos2: int = (line2 * self.width) + col2
                # door opened and neighbor not visited/solution?
                if self.cells[pos] & to_neighbor \
                        and not self.cells[pos2] & visited_solution:
                    self.cells[pos2] |= visited_solution
                    self.solution.append((col2, line2, True))
                    stack.append((col, line))
                    col, line = col2, line2
                    break
            else:
                if not self.cells[-1] & self.SOLUTION:
                    self.cells[pos] &= ~(self.SOLUTION)
                    self.solution.append((col, line, False))
                col, line = stack.pop()
                if not stack:
                    break
        self.display()
        if interactive:
            self.show_interactive_solution()

    def reset(self) -> None:
        """Remove solution."""
        self.remove_timer()
        for index, cell in enumerate(self.cells):
            self.cells[index] = cell & ~(self.SOLUTION | self.SOLUTION_INT)
        self.display()

    def display_line(self, line: int) -> None:
        """Display a line of maze."""
        str_line: str
        if line >= self.height:
            str_line = (
                weechat.color("white")
                + ("▀" * ((self.width * 2) + 1))
            )
        else:
            both_sol: int = self.SOLUTION | self.SOLUTION_INT
            cell: int = self.cells[line * self.width]
            color: str = (
                "lightred" if cell & self.SOLUTION_INT
                else "blue" if cell & self.SOLUTION
                else "black"
            )
            str_line = (
                weechat.color(f"{color},white")
                + ("▄" if cell & self.LEFT else " ")
            )
            for col in range(self.width):
                cell = self.cells[(line * self.width) + col]
                color = (
                    "lightred" if cell & self.SOLUTION_INT
                    else "blue" if cell & self.SOLUTION
                    else "black"
                )
                # door opened on top?
                if cell & self.TOP:
                    pos: int = ((line - 1) * self.width) + col
                    if line > 0 and self.cells[pos] & both_sol:
                        str_line += weechat.color(f"white,{color}") + " "
                    else:
                        str_line += weechat.color(f"{color},black") + "▄"
                else:
                    str_line += weechat.color(f"{color},white") + "▄"
                # door opened on the right?
                str_line += (
                    weechat.color(f"{color},white")
                    + ("▄" if cell & self.RIGHT else " ")
                )
        str_line += weechat.color("reset")
        weechat.prnt_y(self.buffer, line, str_line)

    def display(self) -> None:
        """Display maze."""
        if not self.buffer:
            return
        weechat.buffer_clear(self.buffer)
        for line in range(self.height + 1):
            self.display_line(line)

    def remove_timer(self) -> None:
        """Reset the timer used to show interactive solution."""
        if self.timer:
            weechat.unhook(self.timer)
            self.timer = ""

    def show_interactive_solution(self) -> None:
        """Show solution."""
        self.remove_timer()
        self.timer = weechat.hook_timer(1, 0, 0, "maze_timer_cb", "")

    def show_next_solution(self) -> None:
        """Show next solution step."""
        col: int
        line: int
        show: bool
        col, line, show = self.solution.pop(0)
        pos: int = (line * self.width) + col
        if show:
            self.cells[pos] |= self.SOLUTION_INT
        else:
            self.cells[pos] &= ~(self.SOLUTION_INT)
        self.display_line(line)
        if not self.solution:
            self.remove_timer()

    def __del__(self) -> None:
        """Destructor."""
        self.remove_timer()


maze: Optional[Maze] = None


def maze_input_buffer(data: str, buffer: str, str_input: str) -> int:
    """Input data in maze buffer."""
    # pylint: disable=unused-argument
    if str_input.lower() == "q":
        weechat.buffer_close(buffer)
    else:
        weechat.command("", f"/{SCRIPT_COMMAND} {str_input}")
    return weechat.WEECHAT_RC_OK


def maze_close_buffer(data: str, buffer: str) -> int:
    """Called when maze buffer is closed."""
    # pylint: disable=unused-argument
    global maze
    maze = None
    return weechat.WEECHAT_RC_OK


def maze_timer_cb(data: str, remaining_calls: int) -> int:
    """Timer used to show solution, one cell by one cell."""
    global maze
    if maze:
        maze.show_next_solution()
    return weechat.WEECHAT_RC_OK


def maze_get_size(args: str = "") -> Tuple[int, int]:
    """Get maze size with args, defaulting to current maze or window size."""
    global maze
    width: int = 0
    height: int = 0
    if args in ("d", "default"):
        args = ""
    elif maze:
        width, height = maze.width, maze.height
    if args:
        # size given by user
        try:
            items = args.split()
            if len(items) > 1:
                width, height = int(items[0]), int(items[1])
            else:
                width, height = int(args), int(args)
            width = max(width, 2)
            height = max(height, 2)
        except ValueError:
            width, height = 0, 0
    if not width or not height:
        # automatic size with size of window
        win_width: int = weechat.window_get_integer(weechat.current_window(),
                                                    "win_chat_width") - 1
        win_height: int = weechat.window_get_integer(weechat.current_window(),
                                                     "win_chat_height") - 1
        size: int = min(win_width, win_height)
        width, height = size, size
    return width, height


def maze_get_other_size(pct_diff: int) -> Tuple[int, int]:
    """Get another size using a percent of size to add or subtract."""
    factor: int = pct_diff // abs(pct_diff)
    width: int
    height: int
    width, height = maze_get_size()
    add_width: int = max(2, (width * abs(pct_diff)) // 100)
    add_height: int = max(2, (height * abs(pct_diff)) // 100)
    width += factor * add_width
    height += factor * add_height
    return max(width, 2), max(height, 2)


def maze_new(width: int, height: int) -> None:
    """Create a new maze."""
    global maze
    maze = Maze(width=width, height=height)
    maze.generate()
    maze.display()


def maze_cmd_cb(data: str, buffer: str, args: str) -> int:
    """The /maze command."""
    global maze
    width: int
    height: int
    if args in ("s", "solve"):
        if maze:
            maze.solve()
    elif args in ("i", "isolve"):
        if maze:
            maze.solve(interactive=True)
    elif args in ("r", "reset"):
        if maze:
            maze.reset()
    else:
        if args == "+":
            width, height = maze_get_other_size(30)
        elif args == "-":
            width, height = maze_get_other_size(-30)
        elif args in ("d", "default"):
            width, height = maze_get_size(args)
        elif not args or args in ("n", "new"):
            width, height = maze_get_size()
        else:
            error = weechat.prefix("error")
            weechat.prnt("", f"{error}maze error: unknown option \"{args}\"")
            return weechat.WEECHAT_RC_OK
        maze_new(width, height)
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and IMPORT_OK:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat.hook_command(
            SCRIPT_COMMAND,
            "Generate and solve a maze.",
            "size || n|new || d|default || s|solve || i|isolve || r|reset "
            "|| +|-",
            """\
   size: one size (square) or width and height separated by spaces
    new: regenerate another maze
default: regenerate another maze with default size
  solve: solve the maze and show solution (in blue)
 isolve: solve then show interactively how solution was found (in red)
  reset: hide solution
      +: show a bigger maze
      -: show a smaller maze

All options shown above can be given in input of maze buffer.
""",
            "",
            "maze_cmd_cb",
            "",
        )
