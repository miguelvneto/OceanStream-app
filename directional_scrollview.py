"""Horizontal scrolling with per-touch direction arbitration for nested views.

Use Kivy's on_scroll_* protocol: the ancestor already owns/grabs the touch.
Returning False on a vertical move lets that ancestor start its native scroll.
"""
from functools import partial

from kivy.clock import Clock
from kivy.properties import NumericProperty
from kivy.uix.scrollview import ScrollView


class DirectionalHorizontalScrollView(ScrollView):
    direction_threshold = NumericProperty('8dp')

    def __init__(self, **kwargs):
        self._direction_touches = {}
        super().__init__(**kwargs)

    def _direction_key(self):
        # Native on_touch_move dispatches on_scroll_move only with an sv.* key.
        return self._get_uid('sv.direction')

    def on_scroll_start(self, touch, check_children=True):
        # Keep the native wheel/trackpad path; finger drags use arbitration.
        if 'button' in touch.profile and touch.button.startswith('scroll'):
            return super().on_scroll_start(touch, check_children)
        key = self._direction_key()
        if key in touch.ud:
            return touch.ud[key]['axis'] != 'vertical'
        if not self.collide_point(*touch.pos):
            return False
        if self.disabled:
            return True
        touch.ud[key] = {'axis': None, 'native': False, 'tap': True}
        self._direction_touches[touch.uid] = touch
        # Reserve until the direction is known. Do not start an effect or a
        # scroll_timeout timer: a slow finger must still be classifiable.
        return True

    def on_scroll_move(self, touch):
        state = touch.ud.get(self._direction_key())
        if state is None:
            return False
        if max(abs(touch.x - touch.ox), abs(touch.y - touch.oy)) >= self.direction_threshold:
            state['tap'] = False
        if state['axis'] is None:
            # Kivy transforms both current and original coordinates together.
            dx, dy = abs(touch.x - touch.ox), abs(touch.y - touch.oy)
            if max(dx, dy) < self.direction_threshold or dx == dy:
                return True
            state['axis'] = 'vertical' if dy > dx else 'horizontal'
            if state['axis'] == 'horizontal':
                # A native ScrollView has one kinetic effect per axis. Another
                # finger must not reset the effect owned by the first finger.
                if self._touch is None or self._touch is touch:
                    self._touch = None
                    super().on_scroll_start(touch, check_children=False)
                    native = touch.ud.get(self._get_uid())
                    if native is not None:
                        native['mode'] = 'scroll'
                        state['native'] = True
        if state['axis'] == 'vertical':
            return False
        if state['native']:
            super().on_scroll_move(touch)
        # Even at horizontal overscroll boundaries, keep the chosen axis.
        return True

    def on_scroll_stop(self, touch, check_children=True):
        state = touch.ud.get(self._direction_key())
        if state is None:
            if 'button' in touch.profile and touch.button.startswith('scroll'):
                return super().on_scroll_stop(touch, check_children)
            return False
        try:
            if state['axis'] == 'vertical':
                return False
            if state['native']:
                super().on_scroll_stop(touch, check_children=False)
            elif (state['axis'] is None and state['tap']
                  and max(abs(touch.x - touch.ox), abs(touch.y - touch.oy)) < self.direction_threshold):
                # Preserve tap delivery without starting/stopping a scroll effect.
                self.simulate_touch_down(touch)
                Clock.schedule_once(partial(self._do_touch_up, touch), .2)
            return True
        finally:
            self._forget_direction(touch)

    def _forget_direction(self, touch):
        touch.ud.pop(self._direction_key(), None)
        self._direction_touches.pop(touch.uid, None)
        if self._touch is touch:
            self._touch = None
        touch.ungrab(self)

    def cancel_touch(self, touch):
        """Discard a cancelled gesture without synthesizing a tap or momentum.

        Kivy touch providers normally finish via on_touch_up/on_scroll_stop.
        This also supports explicit cancellation and removal of the card.
        """
        state = touch.ud.get(self._direction_key())
        if state and state['native'] and self._touch is touch:
            if self.effect_x:
                self.effect_x.velocity = 0
                self.effect_x.cancel()
            touch.ud.pop(self._get_uid(), None)
        self._forget_direction(touch)

    def on_parent(self, instance, parent):
        if parent is None:
            for touch in list(self._direction_touches.values()):
                self.cancel_touch(touch)
