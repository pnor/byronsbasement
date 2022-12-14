#!/usr/bin/env python3

"""
Estimate the location of LEDs in 2D space based on how they are arranged
"""

import numpy as np
from functools import lru_cache
from typing import List, Optional, Tuple
from smartquadtree import Quadtree
from numba import jit

from backend.util import distance_formula
from backend.mru_cache import mru_cache


class LED:
    def __init__(self, x: float, y: float, index: int):
        self._x = x
        self._y = y
        self._index = index

    def get_x(self) -> float:
        return self._x

    def get_y(self) -> float:
        return self._y

    def as_tuple(self) -> Tuple[float, float, int]:
        return (self._x, self._y, self._index)

    def __str__(self) -> str:
        return "LED(x: %s, y: %s, index: %s)" % (self._x, self._y, self._index)

    def __repr__(self) -> str:
        return "LED(x: %s, y: %s, index: %s)" % (self._x, self._y, self._index)


class LEDSpace:
    """
    Maintains estimated locations of LEDs in 2D space. Can query locations in the space to get the
    nearest LED for that location.

    The 2D space is a 1x1 square, with x going from (0..1) and y going from (0..1)
    """

    def __init__(self) -> None:
        self._quadtree = Quadtree(0.5, 0.5, 1, 1)
        # pickling
        self._saved_values: Optional[List[LED]] = None

    def map_LEDs_in_zigzag(self, lights_per_row: List[int]) -> None:
        """
        Map LEDs based on the row information in `lights_per_row` to positions in 2D space.
        Asssumes LEDs are layed out like so:

                ----->
        3 ------
         <-----
               ----- 2
                ---->
        1 ------
         <-----
               ----- 0

        `lights_per_row`: first index represents the bottomost row, closest to the data connection
        of the pi

        Each row moves diagonally upwards towards the next row. We map LEDs using the assumption
        that they are equally spaced.
        """
        self._quadtree = Quadtree(0.5, 0.5, 1, 1)
        index = 0

        if len(lights_per_row) == 1:
            row_height = 1
        else:
            row_height = 1 / len(lights_per_row)

        for i in range(len(lights_per_row)):
            for j in range(lights_per_row[i]):
                if i % 2 == 0:  # backward diagonal
                    x = 1 - ((j + 1) / lights_per_row[i])
                    y = (i * row_height) + ((j / lights_per_row[i]) * row_height)
                else:  # forward diagonal
                    x = j / lights_per_row[i]
                    y = (i * row_height) + ((j / lights_per_row[i]) * row_height)
                led = LED(x, y, index)
                self._quadtree.insert(led)
                index += 1

    @lru_cache(maxsize=1000)
    # @mru_cache(maxsize=1000)
    def get_LEDs_in_area(
        self, x: float, y: float, width: float, height: float
    ) -> List[LED]:
        """
        `width`: width of box centered on `(x, y)`
        `height`: height of box centered on `(x, y)`
        """

        left = x - (width / 2)
        right = x + (width / 2)
        bot = y - (height / 2)
        top = y + (height / 2)

        if self._quadtree is None:
            self.restore_quadtree()

        self._quadtree.set_mask([(left, bot), (left, top), (right, top), (right, bot)])

        res: List[LED] = []
        for led in self._quadtree.elements():
            res += [led]

        self._quadtree.set_mask(None)

        return res

    @lru_cache(maxsize=1000)
    # @mru_cache(maxsize=1000)
    def get_LEDs_in_radius(self, x: float, y: float, radius: float) -> List[LED]:
        """
        `radius` around (x, y) of points should be returned
        """
        if self._quadtree is None:
            self.restore_quadtree()

        self._quadtree.set_mask(_mask_for_radius(x, y, radius, 10))

        res: List[LED] = []
        for led in self._quadtree.elements():
            res += [led]

        self._quadtree.set_mask(None)

        return res

    @lru_cache(maxsize=1000)
    # @mru_cache(maxsize=1000)
    def get_closest_LED_index(
        self, x: float, y: float, max_distance: float = 0.30
    ) -> Optional[int]:
        """
        `max_distance` is the largest distance a point will be returned from the queried point querying for specific
        location in 2D space
        """
        results = self.get_LEDs_in_area(x, y, max_distance * 2, max_distance * 2)

        closest: Optional[LED] = None
        closest_distance = 9999999
        for led in results:
            distance = distance_formula(x, y, led.get_x(), led.get_y())
            if distance > max_distance:
                continue
            if closest is None or distance < closest_distance:
                closest = led
                closest_distance = distance

        return None if closest is None else closest._index

    def save_quadtree_values_in_list(self) -> None:
        """Save all the values in the quadtree to a python list
        Quadtree cannot be pickled, so this function allows this object to be pickled by unsetting
        the quadtree temoproraily and restoring it when used
        """
        if self._quadtree is None and self._saved_values is not None:
            # already saved values, and did not restore
            return

        self._quadtree.set_mask(None)
        self._saved_values = []
        for led in self._quadtree.elements():
            self._saved_values += [led]
        self._quadtree = None

    def restore_quadtree(self) -> None:
        """Restores the quadtree from saved values in `self._saved_values`."""
        if self._saved_values is None:
            return
        self._quadtree = Quadtree(0.5, 0.5, 1, 1)
        for v in self._saved_values:
            self._quadtree.insert(v)
        self._saved_values = None

    def clear_caches(self) -> None:
        """
        Clear cached values
        """
        LEDSpace.get_LEDs_in_area.cache_clear()
        LEDSpace.get_closest_LED_index.cache_clear()
        LEDSpace.get_LEDs_in_radius.cache_clear()


@jit(nopython=True, fastmath=True)
def _mask_for_radius(
    x: float, y: float, radius: float, number_points: int
) -> List[Tuple[float, float]]:
    """Helper to create the set of points needed to make a mask for the quadtree
    enacpsulating a circular area"""
    points: List[Tuple[float, float]] = [(0.0, 0.0)] * number_points
    i = 0
    for theta in np.arange(0, 2 * np.pi, (2 * np.pi) / number_points):
        _x = np.cos(theta) * radius
        _y = np.sin(theta) * radius
        _x += x
        _y += y
        points[i] = (_x, _y)
        i += 1
    return points
