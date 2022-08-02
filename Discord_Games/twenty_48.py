from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from io import BytesIO
import asyncio
import random
import pathlib

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from .utils import executor

if TYPE_CHECKING:
    Board = list[list[int]]

class Twenty48:
    player: discord.Member

    def __init__(
        self, 
        number_to_display_mapping: dict[str, str] = {},
        *,
        render_image: bool = False,
    ) -> None:

        self.board: Board = [[0 for _ in range(4)] for _ in range(4)]
        self.message: Optional[discord.Message] = None

        self._controls = ['➡️', '⬅️', '⬇️', '⬆️']
        self._conversion = number_to_display_mapping
        self._render_image = render_image

        if self._render_image and discord.version_info.major < 2:
            raise ValueError('discord.py versions under v2.0.0 do not support rendering images since editing files is new in 2.0')

        if self._render_image:
            self._color_mapping: dict[str, tuple[tuple[int, int, int], int]] = {
                "0": ((204, 192, 179), 50), 
                "2": ((237, 227, 217), 50), 
                "4": ((237, 224, 200), 50), 
                "8":  ((242, 177, 121), 50), 
                "16": ((245, 149, 100), 50), 
                "32": ((246, 124, 95), 50), 
                "64": ((246, 94, 59), 50), 
                "128": ((236, 206, 113), 40),
                "256": ((236, 203, 96), 40),
                "512": ((236, 199, 80), 40),
                "1024": ((236, 196, 62), 30),
                "2048": ((236, 193, 46), 30),
                "4096": ((59, 57, 49), 30),
                "8192": ((59, 57, 49), 30),
            }

            self.LIGHT_CLR = (249, 246, 242)
            self.DARK_CLR = (119, 110, 101)
            self.BG_CLR = (187, 173, 160)

            self.BORDER_W = 20
            self.SQ_S = 100  
            self.SPACE_W = 15

            self.IMG_LENGTH = self.BORDER_W * 2 + self.SQ_S * 4 + self.SPACE_W * 3

            self._font = ImageFont.truetype(
                fr'{pathlib.Path(__file__).parent}\assets\ClearSans-Bold.ttf', 50
            )
        
    def _reverse(self, board: Board) -> Board:
        return [row[::-1] for row in board]

    def _transp(self, board: Board) -> Board:
        return [[board[i][j] for i in range(4)] for j in range(4)]

    def _merge(self, board: Board) -> Board:
        for i in range(4):
            for j in range(3):
                tile = board[i][j]
                if tile == board[i][j + 1] and tile != 0:
                    board[i][j] *= 2
                    board[i][j + 1] = 0
        return board
            
    def _compress(self, board: Board) -> Board:
        new_board = [[0 for _ in range(4)] for _ in range(4)]
        for i in range(4):
            pos = 0
            for j in range(4):
                if board[i][j] != 0:
                    new_board[i][pos] = board[i][j]
                    pos += 1
        return new_board

    def move_left(self) -> None:
        stage = self._compress(self.board)
        stage = self._merge(stage)
        stage = self._compress(stage)
        self.board = stage
        
    def move_right(self) -> None:
        stage = self._reverse(self.board)
        stage = self._compress(stage)
        stage = self._merge(stage)
        stage = self._compress(stage)
        stage = self._reverse(stage)
        self.board = stage
        
    def move_up(self) -> None:
        stage = self._transp(self.board)
        stage = self._compress(stage)
        stage = self._merge(stage)
        stage = self._compress(stage)
        stage = self._transp(stage)
        self.board = stage
        
    def move_down(self) -> None:
        stage = self._transp(self.board)
        stage = self._reverse(stage)
        stage = self._compress(stage)
        stage = self._merge(stage)
        stage = self._compress(stage)
        stage = self._reverse(stage)
        stage = self._transp(stage)
        self.board = stage

    def spawn_new(self) -> None:
        board  = self.board
        zeroes = [(j, i) for j, sub in enumerate(board) for i, el in enumerate(sub) if el == 0]

        if not zeroes:
            return

        i, j = random.choice(zeroes)
        board[i][j] = 2

    def number_to_emoji(self) -> str:
        board = self.board
        emoji_array = [
            [self._conversion.get(str(l), f'`{l}` ') for l in row] 
            for row in board
        ]

        return "".join("".join(row) + "\n" for row in emoji_array)

    @executor()
    def render_image(self) -> discord.File:
        SQ = self.SQ_S
        with Image.new('RGB', (self.IMG_LENGTH, self.IMG_LENGTH), self.BG_CLR) as img:
            cursor = ImageDraw.Draw(img)

            x = y = self.BORDER_W
            for row in self.board:
                for tile in row:
                    tile = str(tile)
                    color, fsize = self._color_mapping.get(tile)
                    font = self._font.font_variant(size=fsize)
                    cursor.rounded_rectangle((x, y, x+SQ, y+SQ), radius=5, width=0, fill=color)

                    if tile != '0':
                        text_fill = self.DARK_CLR if tile in {'2', '4'} else self.LIGHT_CLR
                        cursor.text((x+SQ/2, y+SQ/2), tile, font=font, anchor='mm', fill=text_fill)

                    x += SQ + self.SPACE_W
                x = self.BORDER_W
                y += SQ + self.SPACE_W

            buf = BytesIO()
            img.save(buf, 'PNG')
        buf.seek(0)
        return discord.File(buf, '2048.png')

    async def start(
        self, 
        ctx: commands.Context, 
        *, 
        timeout: Optional[float] = None,
        remove_reaction_after: bool = True, 
        delete_button: bool = False, 
        **kwargs,
    ) -> None:

        self.player = ctx.author
        self.board[random.randrange(4)][random.randrange(4)] = 2
        self.board[random.randrange(4)][random.randrange(4)] = 2
        
        if self._render_image:
            image = await self.render_image()
            self.message = await ctx.send(file=image, **kwargs)
        else:
            board_string = self.number_to_emoji()
            self.message = await ctx.send(board_string, **kwargs)

        if delete_button:
            self._controls.append("⏹️")

        for button in self._controls:
            await self.message.add_reaction(button)

        while True:

            def check(reaction, user):
                return str(reaction.emoji) in self._controls and user == self.player and reaction.message == self.message
            
            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
            except asyncio.TimeoutError:
                return False

            emoji = str(reaction.emoji)

            if delete_button and emoji == "⏹️":
                return await self.message.delete()

            if emoji == '➡️':
                self.move_right()

            elif emoji == '⬅️':
                self.move_left()

            elif emoji == '⬇️':
                self.move_down()

            elif emoji == '⬆️':
                self.move_up()

            if remove_reaction_after:
                try:
                    await self.message.remove_reaction(emoji, user)
                except discord.DiscordException:
                    pass

            self.spawn_new()

            if self._render_image:
                image = await self.render_image()
                await self.message.edit(attachments=[image])
            else:
                board_string = self.number_to_emoji()
                await self.message.edit(content=board_string)