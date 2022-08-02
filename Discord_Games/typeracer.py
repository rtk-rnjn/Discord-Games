from __future__ import annotations

from typing import Optional, ClassVar, Any
from datetime import datetime as dt
from io import BytesIO

import textwrap
import time
import random
import asyncio
import aiohttp
import difflib
import pathlib

from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands

from .utils import *


class TypeRacer:
    SENTENCE_URL: ClassVar[str] = "https://api.quotable.io/random"
    GRAMMAR_WORDS: ClassVar[tuple[str]] = (
        'the', 'of', 'to', 'and', 'a', 'in', 'is', 'it',
        'you', 'that', 'he', 'was', 'for', 'on', 'are',
        'with', 'as', 'his', 'they', 'be', 'at', 'one',
        'have', 'this', 'from', 'or', 'had', 'by', 'not',
        'word', 'but', 'what', 'some', 'we', 'can', 'out',
        'other', 'were', 'all', 'there', 'when', 'up', 'use',
        'your', 'how', 'said', 'an', 'each', 'she', 'which',
        'do', 'their', 'time', 'if', 'will', 'way', 'about',
        'many', 'then', 'them', 'write', 'would', 'like', 'so',
        'these', 'her', 'long', 'make', 'thing', 'see', 'him',
        'two', 'has', 'look', 'more', 'day', 'could', 'go', 'come',
        'did', 'number', 'sound', 'no', 'most', 'people', 'my',
        'over', 'know', 'water', 'than', 'call', 'first', 'who',
        'may', 'down', 'side', 'been', 'now', 'find', 'any', 'new',
        'work', 'part', 'take', 'get', 'place', 'made', 'live',
        'where', 'after', 'back', 'little', 'only', 'round', 'man',
        'year', 'came', 'show', 'every', 'good', 'me', 'give', 'our',
        'under', 'name', 'very', 'through', 'just', 'form', 'sentence',
        'great', 'think', 'say', 'help', 'low', 'line', 'differ', 'turn',
        'cause', 'much', 'mean', 'before', 'move', 'right', 'boy', 'old',
        'too', 'same', 'tell', 'does', 'set', 'three', 'want', 'air', 'well',
        'also', 'play', 'small', 'end', 'put', 'home', 'read', 'hand', 'port',
        'large', 'spell', 'add', 'even', 'land', 'here', 'must', 'big', 'high',
        'such', 'follow', 'act', 'why', 'ask', 'men', 'change', 'went', 'light',
        'kind', 'off', 'need', 'house', 'picture', 'try', 'us', 'again', 'animal',
        'point', 'mother', 'world', 'near', 'build', 'self', 'earth', 'father', 'head',
        'stand', 'own', 'page', 'should', 'country', 'found', 'answer', 'school',
        'grow', 'study', 'still', 'learn', 'plant', 'cover', 'food', 'sun', 'four',
        'between', 'state', 'keep', 'eye', 'never', 'last', 'let', 'thought', 'city',
        'tree', 'cross', 'farm', 'hard', 'start', 'might', 'story', 'saw', 'far',
        'sea', 'draw', 'left', 'late', 'run', "don't", 'while', 'press', 'close',
        'night', 'real', 'life', 'few', 'north'
    )
    EMOJI_MAP: ClassVar[dict[int, str]] = {
        1: "🥇", 
        2: "🥈", 
        3: "🥉",
    }

    @executor()
    def _tr_img(self, text: str, font: str) -> BytesIO:

        text = "\n".join(textwrap.wrap(text, width=25))

        font = ImageFont.truetype(font, 30)
        x, y = font.getsize_multiline(text)

        with Image.new("RGB", (x+20, y+30), (0, 0, 30)) as image:
            cursor = ImageDraw.Draw(image)
            cursor.multiline_text((10, 10), text, font=font, fill=(220, 200, 220))

            buffer = BytesIO()
            image.save(buffer, "PNG")
            buffer.seek(0)
            return buffer

    def format_line(self, i: int, x: dict[str, Any]) -> str:
        return f" • {self.EMOJI_MAP[i]} | {x['user'].mention} in {x['time']:.2f}s | **WPM:** {x['wpm']:.2f} | **ACC:** {x['acc']:.2f}%"

    async def wait_for_tr_response(self, ctx: commands.Context, text: str, *, timeout: int) -> discord.Message:

        self._embed.description = ""

        text = text.lower().replace("\n", " ")
        winners = []
        start = time.perf_counter()

        while True:

            def check(m: discord.Message) -> bool:
                content = m.content.lower().replace("\n", " ")
                if m.channel == ctx.channel and not m.author.bot and m.author not in map(lambda m: m["user"], winners):
                    sim = difflib.SequenceMatcher(None, content, text).ratio()
                    return sim >= 0.9

            try:
                message: discord.Message = await ctx.bot.wait_for("message", timeout=timeout, check=check)
            except asyncio.TimeoutError:
                if winners:
                    break
                else:
                    return await ctx.reply("Looks like no one responded", allowed_mentions=discord.AllowedMentions.none())

            end = time.perf_counter()
            content = message.content.lower().replace("\n", " ")
            timeout -= round(end - start)

            winners.append({
                "user": message.author, 
                "time": end - start, 
                "wpm" : len(text.split(" ")) / ((end - start) / 60), 
                "acc" : difflib.SequenceMatcher(None, content, text).ratio() * 100
            })

            self._embed.description += self.format_line(len(winners), winners[-1]) + "\n"
            await self._message.edit(embed=self._embed)

            await message.add_reaction(self.EMOJI_MAP[len(winners)])

            if len(winners) >= 3:
                break

        desc = [self.format_line(i, x) for i, x in enumerate(winners, 1)]
        embed = discord.Embed(
            title="Typerace results",
            color=self.embed_color, 
            timestamp=dt.utcnow()
        )
        embed.add_field(name="Winners", value="\n".join(desc))

        return await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    async def start(
        self, 
        ctx: commands.Context, 
        *, 
        embed_title: str = "Type the following sentence in the chat now!", 
        embed_color: DiscordColor = DEFAULT_COLOR, 
        path_to_text_font: Optional[str] = None,
        timeout: Optional[float] = None, 
        words_mode: bool = False,
        show_author: bool = True,
    ) -> discord.Message:

        self.embed_color = embed_color

        if not words_mode:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.SENTENCE_URL) as r:
                    if not r.ok:
                        raise RuntimeError(f"HTTP request raised an error: {r.status}; {r.reason}")

                    text = await r.json()
                    text = text.get("content")
        else:
            text = " ".join(random.choice(self.GRAMMAR_WORDS).lower() for _ in range(15))

        if not path_to_text_font:
            path_to_text_font = fr'{pathlib.Path(__file__).parent}\assets\segoe-ui-semilight-411.ttf'

        buffer = await self._tr_img(text, path_to_text_font)

        embed = discord.Embed(
            title=embed_title,
            color=self.embed_color, 
            timestamp=dt.utcnow()
        )
        embed.set_image(url="attachment://tr.png")

        if show_author:
            if discord.version_info.major >= 2:
                av = ctx.author.avatar.url
            else:
                av = ctx.author.avatar_url
            embed.set_author(name=ctx.author.name, icon_url=av)

        self._embed = embed
        self._message = await ctx.send(
            embed=embed,
            file=discord.File(buffer, "tr.png")
        )

        return await self.wait_for_tr_response(ctx, text, timeout=timeout)