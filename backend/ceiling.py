#!/usr/bin/env python3

from typing import Callable, Any, Optional, List, Tuple
from typing_extensions import Self
from backend.cartesian_indexing import CartesianIndexing
from backend.float_cartesian import FloatCartesianIndexing
from backend.float_polar import FloatPolarIndexing
from backend.led_locations import LEDSpace
from backend.linear_indexing import LinearIndexing
from backend.neopixel_wrapper import (
    init_for_testing,
    init_with_real_board,
)
from backend.polar_indexing import PolarIndexing
from backend.row_indexing import RowIndexing


from .backend_types import RGB

from .indexing import *

"""
A layer between the neopixel API and our light scripts to abstract away all that coordinate math
"""

# Basement related constants
NUMBER_LIGHTS = 200
CEILING_ROW_ARRANGEMENT = [29, 29, 32, 29, 32, 28, 20]


class Ceiling:
    def __init__(self, **kwargs):
        """
        If using actual light strip:
        `io_pin`: which GPIO pin neopixels should be initialized for
        `number_lights`: number lights controlled
        `auto_write`: whether every write to the neopixels LED array should update the lights. *False*
        by default(!!!)

        If using testing: (only provide 2 args)
        `test_mode`: to true
        `number_lights`: number lights in the light strip
        `print_to_stdout`: whether to print to stdout. Default true
        """
        # Initialize for testing mode
        # For running not on a Pi
        if kwargs.get("test_mode"):
            opt_number_lights = kwargs.get("number_lights")
            if opt_number_lights and type(opt_number_lights) is int:
                number_lights = opt_number_lights
            else:
                number_lights = NUMBER_LIGHTS

            opt_print_to_stdout = kwargs.get("print_to_stdout")
            if type(opt_print_to_stdout) is bool:
                print_to_stdout = opt_print_to_stdout
            else:
                print_to_stdout = True

            self._pixels = init_for_testing(
                number_leds=number_lights, print_to_stdout=print_to_stdout
            )
            self.testing_mode_rows()
        else:  # For running on the actual pi
            io_pin = kwargs.get("io_pin")

            opt_number_lights = kwargs.get("number_lights")
            if opt_number_lights and type(opt_number_lights) is int:
                number_lights = opt_number_lights
            else:
                number_lights = NUMBER_LIGHTS

            opt_auto_write = kwargs.get("auto_write")
            if opt_auto_write and type(opt_auto_write) is bool:
                auto_write = opt_auto_write
            else:
                auto_write = False

            self._pixels = init_with_real_board(
                io_pin, number_lights, auto_write=auto_write
            )

        self._indexing = LinearIndexing(self._pixels)
        self.NUMBER_LIGHTS = NUMBER_LIGHTS
        self._cached_led_spacing: Optional[LEDSpace] = None

    # ===== Animation / Clearing ==========

    def clear(self, show=True) -> None:
        """Set every pixel to black (and updates the LEDs)"""
        self.fill([0, 0, 0])
        if show:
            self.show()

    def fill(self, clear_color: RGB) -> None:
        """Set every pixel to the given color"""
        self._pixels.fill(clear_color)

    def show(self) -> None:
        """Update all pixels with updated colors at once"""
        self._pixels.show()

    # ===== Getting / Setting ==========
    def __getitem__(self, key: Any) -> Optional[RGB]:
        return self._indexing.get(key)

    def __setitem__(self, key: Any, value: RGB) -> None:
        self._indexing.set(key, value)

    def rows(self) -> Optional[List[int]]:
        """Returns rows information if the indexing is row indexing"""
        if isinstance(self._indexing, RowIndexing):
            return self._indexing.rows
        else:
            return None

    def testing_mode_rows(self, lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT):
        self._pixels.set_lights_per_row(lights_per_row)

    def indexing(self) -> Indexing:
        """Return the current Indexing object"""
        return self._indexing

    # ===== Async and Sending Between Processes ==========

    def prepare_to_send(self) -> None:
        """
        Prepares the ceiling object to be sent between processes with `Pipe`
        Must call this before sending this with `pipe.send(ceiling)`!
        """
        self._cached_led_spacing = None
        self._pixels.prepare_to_send()
        self._indexing.prepare_to_send()

    # ===== Indexing ==========

    def use_linear(self):
        "Use linear indexing"
        self._indexing = LinearIndexing(self._pixels)

    def with_linear(self, block: Callable[[Self], None]) -> None:
        """Execute `block` with the linear indexing method"""
        old_indexing = self._indexing
        self.use_linear()
        block(self)
        self._indexing = old_indexing

    def use_row(self, lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT):
        """Use row based indexing"""
        self._indexing = RowIndexing(self._pixels, lights_per_row)

    def with_row(self, block: Callable[[Self], None]) -> None:
        """Execute `block` with the row indexing method"""
        old_indexing = self._indexing
        self.use_row()
        block(self)
        self._indexing = old_indexing

    def use_cartesian(
        self,
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        search_range: float = 0.2,
    ):
        """Use cartesian indexing"""
        self._indexing = CartesianIndexing(
            self._pixels,
            lights_per_row,
            search_range,
            cached_led_spacing=self._cached_led_spacing,
        )
        self._cached_led_spacing = self._indexing._led_spacing

    def with_cartesian(
        self,
        block: Callable[[Self], None],
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        search_range: float = 0.2,
    ) -> None:
        """Execute `block` with the cartesian indexing method"""
        old_indexing = self._indexing
        self.use_cartesian(lights_per_row, search_range)
        block(self)
        self._indexing = old_indexing

    def use_polar(
        self,
        origin: Tuple[float, float],
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        search_range: float = 0.2,
    ):
        assert len(origin) == 2
        """Use polar indexing"""
        self._indexing = PolarIndexing(
            self._pixels,
            lights_per_row=lights_per_row,
            origin=origin,
            search_range=search_range,
            cached_led_spacing=self._cached_led_spacing,
        )
        self._cached_led_spacing = self._indexing._led_spacing

    def with_polar(
        self,
        block: Callable[[Self], None],
        origin: Tuple[float, float],
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        search_range: float = 0.2,
    ) -> None:
        """Execute `block` with the polar indexing method"""
        old_indexing = self._indexing
        self.use_polar(origin, lights_per_row, search_range=search_range)
        block(self)
        self._indexing = old_indexing

    def use_float_cartesian(
        self,
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        effect_radius: float = 0.2,
    ):
        """Use floating point cartesian indexing"""
        self._indexing = FloatCartesianIndexing(
            self._pixels,
            lights_per_row,
            effect_radius=effect_radius,
            cached_led_spacing=self._cached_led_spacing,
        )
        self._cached_led_spacing = self._indexing._led_spacing

    def with_float_cartesian(
        self,
        block: Callable[[Self], None],
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        effect_radius: float = 0.2,
    ) -> None:
        """Execute `block` with the float cartesian indexing method"""
        old_indexing = self._indexing
        self.use_float_cartesian(lights_per_row, effect_radius)
        block(self)
        self._indexing = old_indexing

    def use_float_polar(
        self,
        origin: Tuple[float, float],
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        effect_radius: float = 0.2,
    ):
        """Use floating point polar indexing"""
        self._indexing = FloatPolarIndexing(
            self._pixels,
            lights_per_row,
            origin,
            effect_radius=effect_radius,
            cached_led_spacing=self._cached_led_spacing,
        )
        self._cached_led_spacing = self._indexing._led_spacing

    def with_float_polar(
        self,
        block: Callable[[Self], None],
        origin: Tuple[float, float],
        lights_per_row: List[int] = CEILING_ROW_ARRANGEMENT,
        effect_radius: float = 0.2,
    ) -> None:
        """Execute `block` with the float polar indexing method"""
        old_indexing = self._indexing
        self.use_float_polar(origin, lights_per_row, effect_radius)
        block(self)
        self._indexing = old_indexing
