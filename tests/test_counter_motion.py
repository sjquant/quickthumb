"""Behavioral specifications for how an animated numeric value moves."""

from quickthumb import Canvas

FONT = "assets/fonts/Roboto-Medium.ttf"


def counter_canvas(**options):
    """Place one odometer counter on a dark canvas."""
    defaults = {
        "position": (30, 20),
        "size": 88,
        "color": "#E8A552",
        "font": FONT,
        "style": "odometer",
    }
    return Canvas(460, 150).background(color="#0A0E12").counter(**{**defaults, **options})


def ink_span(canvas, time):
    """Return the horizontal extent of the counter's ink at a moment."""
    frame = canvas.render_frame(time).convert("RGB")
    lit = [
        x
        for x in range(frame.width)
        if any(sum(frame.getpixel((x, y))) > 200 for y in range(frame.height))
    ]
    return (min(lit), max(lit)) if lit else None


def roll_samples(canvas, start=0.2, step=0.02, count=100):
    """Sample the counter's ink across its whole roll."""
    return [ink_span(canvas, start + index * step) for index in range(count)]


class TestCounterDigitHandoff:
    """Digits should roll in place without shuffling the number sideways."""

    def test_should_hold_the_suffix_still_while_the_number_grows(self):
        """Given a counter gaining digits, when it rolls, then its right edge never moves."""
        # Given: a counter running from one digit to three, with a suffix
        canvas = counter_canvas(from_=0, to=100, duration=1.8, delay=0.2, suffix="%")

        # When: the right edge is sampled across the whole animation
        right_edges = {span[1] for span in roll_samples(canvas)}

        # Then: the suffix stays put instead of being pushed along by the digits
        assert len(right_edges) == 1

    def test_should_never_render_wider_than_the_value_it_settles_on(self):
        """Given a counter, when it rolls, then no frame is wider than the final value."""
        # Given: a counter whose widest value is its last one
        canvas = counter_canvas(from_=0, to=100, duration=1.8, delay=0.2, suffix="%")

        # When: every frame's width is compared with the settled width
        settled = ink_span(canvas, 2.4)
        widths = [span[1] - span[0] for span in roll_samples(canvas)]

        # Then: nothing overflows the box the counter reserves for itself
        assert max(widths) <= settled[1] - settled[0]

    def test_should_leave_the_leading_slot_empty_until_the_value_reaches_it(self):
        """Given a counter below 100, when rendered, then no hundreds digit is shown."""
        # Given: a counter that only reaches three digits at the very end
        canvas = counter_canvas(from_=0, to=100, duration=1.8, delay=0.2, suffix="%")

        # When: a two-digit moment is compared with the settled three-digit one
        settled = ink_span(canvas, 2.4)
        two_digit = ink_span(canvas, 1.7)
        slot = (settled[1] - settled[0]) / 3

        # Then: the leading slot carries no ink, so 99 never reads as 199
        assert two_digit[0] > settled[0] + slot * 0.5

    def test_should_settle_on_its_target_for_any_digit_count(self):
        """Given finished counters, when rendered, then each shows its own target."""
        # Given: counters that end on different digit counts
        wide = counter_canvas(from_=0, to=100, duration=1.0, suffix="%")
        narrow = counter_canvas(from_=1, to=3, duration=1.0, suffix="x")

        # When: each is rendered well past its duration
        wide_settled = ink_span(wide, 3.0)
        narrow_settled = ink_span(narrow, 3.0)

        # Then: both draw a stable value and the wider target is wider
        assert wide_settled is not None and narrow_settled is not None
        assert wide_settled[1] - wide_settled[0] > narrow_settled[1] - narrow_settled[0]

    def test_should_keep_a_fixed_width_counter_completely_still(self):
        """Given a counter that never changes digit count, when it rolls, then it does not move."""
        # Given: a counter whose values are all two digits wide
        canvas = counter_canvas(from_=10, to=99, duration=1.2, delay=0.1, suffix="x")

        # When: both edges are sampled across the roll
        spans = roll_samples(canvas, start=0.1, step=0.02, count=70)

        # Then: the whole block is anchored. The few pixels of play on the left
        # are the ink bearing of different glyphs inside a fixed slot, not the
        # slot moving: a "1" simply carries less ink than an "8".
        assert len({span[1] for span in spans}) == 1
        assert max(span[0] for span in spans) - min(span[0] for span in spans) <= 6
