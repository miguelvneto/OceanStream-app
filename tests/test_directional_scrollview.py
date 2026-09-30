"""Isolated routing tests: no window, Kivy installation or mobile build needed.

The base double implements the nested on_scroll_* return-value contract.
It records native effect calls; it does not simulate Kivy physics/rendering.
"""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


class Touch:
    serial = 0

    def __init__(self, x=40, y=50):
        Touch.serial += 1
        self.uid = Touch.serial
        self.x = self.ox = x
        self.y = self.oy = y
        self.ud = {}
        self.profile = ['pos']
        self.ungrab = Mock()

    @property
    def pos(self):
        return self.x, self.y

    def move(self, dx, dy):
        self.x, self.y = self.ox + dx, self.oy + dy


class NativeScrollDouble:
    def __init__(self, **kwargs):
        self._touch = None
        self.disabled = False
        self.effect_x = Mock()
        self.events = []
        self.simulate_touch_down = Mock()
        self._do_touch_up = Mock()
        self.__dict__.update(kwargs)

    def _get_uid(self, suffix=''):
        return suffix + '.' + str(id(self))

    def collide_point(self, x, y):
        return True

    def on_scroll_start(self, touch, check_children=True):
        self.events.append(('start', touch.uid))
        self._touch = touch
        touch.ud[self._get_uid()] = {'mode': 'unknown'}
        self.effect_x.start(touch.x)
        return True

    def on_scroll_move(self, touch):
        self.events.append(('move', touch.uid))
        self.effect_x.update(touch.x)
        # Deliberately emulate overscroll: the subclass must keep X locked.
        return False

    def on_scroll_stop(self, touch, check_children=True):
        self.events.append(('stop', touch.uid))
        self.effect_x.stop(touch.x)
        self._touch = None
        return True


class VerticalParent:
    """Ancestor receives False from its nested child and starts native Y."""
    def __init__(self, child):
        self.child = child
        self.started = False
        self.moves = 0
        self.stops = 0

    def down(self, touch):
        return self.child.on_scroll_start(touch)

    def move(self, touch):
        if not self.child.on_scroll_move(touch):
            if self.started:
                self.moves += 1
            else:
                self.started = True

    def up(self, touch):
        if not self.child.on_scroll_stop(touch) and self.started:
            self.stops += 1


def load_view():
    modules = {name: ModuleType(name) for name in
               ['kivy', 'kivy.clock', 'kivy.properties', 'kivy.uix', 'kivy.uix.scrollview']}
    clock = Mock()
    modules['kivy.clock'].Clock = clock
    modules['kivy.properties'].NumericProperty = lambda value: float(value.removesuffix('dp'))
    modules['kivy.uix.scrollview'].ScrollView = NativeScrollDouble
    path = Path(__file__).resolve().parents[1] / 'directional_scrollview.py'
    spec = importlib.util.spec_from_file_location('gesture_test_module', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.DirectionalHorizontalScrollView(), clock


class DirectionalScrollTests(unittest.TestCase):
    def setUp(self):
        self.view, self.clock = load_view()
        self.parent = VerticalParent(self.view)
        self.touch = Touch()
        self.parent.down(self.touch)

    def gesture(self, dx, dy):
        self.touch.move(dx, dy)
        self.parent.move(self.touch)
        self.touch.move(dx * 2, dy * 2)
        self.parent.move(self.touch)
        self.parent.up(self.touch)

    def test_pending_touch_keeps_native_nested_dispatch_enabled(self):
        # Kivy on_touch_move bypasses on_scroll_move without an sv.* key.
        self.assertTrue(any(key.startswith('sv.') for key in self.touch.ud))
        self.view.effect_x.start.assert_not_called()
        self.clock.schedule_once.assert_not_called()

    def test_horizontal(self):
        self.gesture(12, 0)
        self.assertFalse(self.parent.started)
        self.view.effect_x.start.assert_called_once()
        self.view.effect_x.stop.assert_called_once()
        self.assertEqual(self.view.effect_x.update.call_count, 2)

    def test_vertical(self):
        self.gesture(0, 12)
        self.assertTrue(self.parent.started)
        self.assertEqual(self.parent.moves, 1)
        self.assertEqual(self.parent.stops, 1)
        self.view.effect_x.start.assert_not_called()

    def test_diagonal_horizontal(self):
        self.gesture(12, 9)
        self.assertFalse(self.parent.started)
        self.view.effect_x.stop.assert_called_once()

    def test_diagonal_vertical(self):
        self.gesture(9, 12)
        self.assertTrue(self.parent.started)
        self.view.effect_x.start.assert_not_called()

    def test_axis_does_not_switch_even_at_overscroll(self):
        self.touch.move(12, 1)
        self.parent.move(self.touch)
        self.touch.move(13, 100)
        self.parent.move(self.touch)
        self.assertFalse(self.parent.started)
        self.parent.up(self.touch)

    def test_vertical_lock_does_not_switch(self):
        self.touch.move(1, 12)
        self.parent.move(self.touch)
        self.touch.move(100, 13)
        self.parent.move(self.touch)
        self.view.effect_x.start.assert_not_called()
        self.parent.up(self.touch)

    def test_tap_and_small_jitter_never_start_scroll(self):
        self.touch.move(3, 2)
        self.parent.move(self.touch)
        self.parent.up(self.touch)
        self.view.effect_x.start.assert_not_called()
        self.assertFalse(self.parent.started)
        self.view.simulate_touch_down.assert_called_once_with(self.touch)
        callback = self.clock.schedule_once.call_args.args[0]
        callback(0)
        self.view._do_touch_up.assert_called_once_with(self.touch, 0)
        self.assertFalse(self.view._direction_touches)

    def test_exact_diagonal_waits_for_direction(self):
        self.touch.move(12, 12)
        self.parent.move(self.touch)
        self.view.effect_x.start.assert_not_called()
        self.touch.move(13, 15)
        self.parent.move(self.touch)
        self.assertTrue(self.parent.started)
        self.parent.up(self.touch)

    def test_gesture_does_not_affect_next(self):
        self.gesture(0, 12)
        self.assertNotIn(self.view._direction_key(), self.touch.ud)
        self.touch = Touch()
        self.parent = VerticalParent(self.view)
        self.parent.down(self.touch)
        self.gesture(12, 0)
        self.view.effect_x.stop.assert_called_once()
        self.assertFalse(self.parent.started)

    def test_multitouch_directions_are_independent(self):
        second = Touch()
        self.view.on_scroll_start(second)
        self.touch.move(12, 0)
        second.move(0, 12)
        self.assertTrue(self.view.on_scroll_move(self.touch))
        self.assertFalse(self.view.on_scroll_move(second))
        self.view.on_scroll_stop(second)
        self.assertIs(self.view._touch, self.touch)
        self.view.on_scroll_stop(self.touch)
        self.assertFalse(self.view._direction_touches)

    def test_second_horizontal_finger_does_not_reset_effect(self):
        second = Touch()
        self.view.on_scroll_start(second)
        self.touch.move(12, 0)
        second.move(12, 0)
        self.view.on_scroll_move(self.touch)
        self.view.on_scroll_move(second)
        self.view.effect_x.start.assert_called_once()
        self.view.on_scroll_stop(second)
        self.assertIs(self.view._touch, self.touch)
        self.view.on_scroll_stop(self.touch)
        self.view.effect_x.stop.assert_called_once()

    def test_cancel_cleans_state_without_tap_or_momentum(self):
        self.touch.move(12, 0)
        self.parent.move(self.touch)
        self.view.cancel_touch(self.touch)
        self.assertFalse(self.view._direction_touches)
        self.assertIsNone(self.view._touch)
        self.assertEqual(self.view.effect_x.velocity, 0)
        self.view.effect_x.cancel.assert_called_once()
        self.view.effect_x.stop.assert_not_called()
        self.view.simulate_touch_down.assert_not_called()
        self.view.on_scroll_stop(self.touch)
        self.view.effect_x.stop.assert_not_called()

    def test_removal_cancels_pending_touch(self):
        self.view.on_parent(self.view, None)
        self.assertFalse(self.view._direction_touches)
        self.view.simulate_touch_down.assert_not_called()

    def test_coordinates_are_relative_to_touch_origin(self):
        self.parent.up(self.touch)
        self.touch = Touch(500, -200)
        self.parent.down(self.touch)
        self.gesture(9, 12)
        self.assertTrue(self.parent.started)


if __name__ == '__main__':
    unittest.main()
