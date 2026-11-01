"""Render an image, a two-slide presentation, and an animated GIF.

Run from any directory: python /path/to/creative_starter.py
The files are written to the current directory and replaced on subsequent runs.
"""

from quickthumb import Canvas, Deck, Fade, GifOptions


def slide(title: str, subtitle: str) -> Canvas:
    return (
        Canvas(960, 540)
        .background(color="#155BD7")
        .text(title, size=82, color="#FFFFFF", position=(64, 150), animation=Fade(duration=0.5))
        .text(subtitle, size=32, color="#D5E5FF", position=(64, 300))
    )


first = slide("Make an idea visible.", "One canvas, many possibilities.")
second = slide("Keep the story moving.", "Bring canvases together in a deck.")
deck = Deck(960, 540).slide(first).slide(second)

first.render("creative-starter.png")
deck.render("creative-starter.html")
first.render("creative-starter.gif", animation=GifOptions(fps=10, hold=1))
