#!/usr/bin/env python3

try:
    import board
    import neopixel
except:
    print("running not on a rasberry pi")

from microcontroller import Pin
from typing import Optional, List, Any

from backend.test_display import TestDisplay
from backend.backend_types import RGB

"""
Wrapper around the neopixel api to allow for testing without the rasberry pi
"""


class PixelWrapper:
    def __init__(self) -> None:
        """
        Should not be called directly
        Use `init_with_real_board` or `init_for_testing`
        """
        self.print_to_stdout = True
        self._auto_write = True
        self._pixels = None
        self._pretend_pixels = None

    def set_lights_per_row(self, lights_per_row: List[int]) -> None:
        self._lights_per_row = lights_per_row
        self._test_display = TestDisplay(lights_per_row, self)

    def __getitem__(self, key: Any) -> Optional[RGB]:
        if self._pixels:
            return self._pixels.__getitem__(key)
        else:
            return self._pretend_pixels[key]

    def __setitem__(self, key: Any, value: RGB) -> None:
        if self._pixels:
            self._pixels.__setitem__(key, value)
        else:
            self._pretend_pixels[key] = value

        if self._test_display and self._auto_write:
            self._test_display.show()

    def fill(self, color: RGB) -> None:
        if self._pixels:
            self._pixels.show(value)
        else:
            for i in range(len(self._pretend_pixels)):
                self._pretend_pixels[i] = color

        if self._auto_write:
            self.show()

    def show(self):
        if self._test_display and self.print_to_stdout:
            self._test_display.show()


def init_with_real_board(
    io_pin: Optional[Pin], number_lights: int, auto_write: bool
) -> PixelWrapper:
    pixel = PixelWrapper()
    pixel._auto_write = auto_write
    pixel._pixels = neopixel.NeoPixel(
        (io_pin if io_pin else board.D21),
        number_lights,
        auto_write=auto_write,
        pixel_order=neopixel.RGB,
    )
    return pixel


def init_for_testing(number_leds: int) -> PixelWrapper:
    pixel = PixelWrapper()
    pixel._pretend_pixels = [(0, 0, 0)] * number_leds
    return pixel