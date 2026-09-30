"""Equipment-scoped viewer with vector graphics and native swipe navigation."""
from math import hypot, sin, pi

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as TextureLabel
from kivy.core.image import Image as CoreImage
from kivy.resources import resource_find
from kivy.graphics import (Color, Line, Rectangle, RoundedRectangle, Triangle,
                           Ellipse, PushMatrix, PopMatrix, Scale)
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.carousel import Carousel
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from measurement_model import (Measurement, direction_geometry, friendly_timestamp,
                               measurement_ticks, tick_labels, indicator_angle, inclination_geometry, fitted_image_size)

INK = (0.08, 0.18, 0.23, 1)
ACCENT = (0.02, 0.55, 0.61, 1)
MUTED = (.38, .47, .51, 1)
PALE = (.90, .95, .96, 1)


class MeasurementTile(ButtonBehavior, BoxLayout):
    """Only native tap releases open details; transforms never change hit boxes."""
    press_scale = NumericProperty(1)

    def __init__(self, measurement, open_detail, **kwargs):
        self.measurement = measurement
        self.open_detail = open_detail
        super().__init__(**kwargs)
        with self.canvas.before:
            PushMatrix()
            self._scale = Scale(1, 1, 1, origin=(*self.center, 0))
        with self.canvas.after:
            PopMatrix()
        self.bind(press_scale=self._update_scale, center=self._update_scale)

    def _update_scale(self, *args):
        self._scale.x = self._scale.y = self.press_scale
        self._scale.origin = (*self.center, 0)

    def on_press(self):
        Animation.cancel_all(self, 'press_scale')
        Animation(press_scale=.96, duration=.07).start(self)

    def on_release(self):
        Animation.cancel_all(self, 'press_scale')
        Animation(press_scale=1, duration=.12).start(self)
        self.open_detail(self.measurement)


class MeasurementGraphic(Widget):
    progress = NumericProperty(1)

    def __init__(self, measurement, **kwargs):
        self.measurement = measurement
        self._textures = {}
        self._equipment_texture = None
        if measurement.renderer in ('pitch', 'roll'):
            path = resource_find('res/equipamentos/nortek_awac.png')
            if path:
                self._equipment_texture = CoreImage(path).texture
        super().__init__(**kwargs)
        self._redraw = Clock.create_trigger(self._draw, 0)
        self.bind(pos=self._redraw, size=self._redraw, progress=self._redraw)
        self._redraw()

    def animate(self):
        Animation.cancel_all(self, 'progress')
        self.progress = 0
        Animation(progress=1, duration=.35, t='out_cubic').start(self)

    def stop(self):
        Animation.cancel_all(self, 'progress')
        self.progress = 1

    def _text(self, text, x, y, size=14):
        key = (text, size)
        if key not in self._textures:
            label = TextureLabel(text=text, font_size=sp(size), color=MUTED)
            label.refresh()
            self._textures[key] = label.texture
        texture = self._textures[key]
        Color(1, 1, 1, 1)
        Rectangle(texture=texture, pos=(x - texture.width / 2, y - texture.height / 2),
                  size=texture.size)

    def _arrow(self, x0, y0, x1, y1):
        Color(*ACCENT)
        Line(points=[x0, y0, x1, y1], width=dp(2.5))
        length = max(hypot(x1 - x0, y1 - y0), 1)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        tip = dp(12)
        Triangle(points=[x1, y1, x1 - ux * tip - uy * tip / 2,
                         y1 - uy * tip + ux * tip / 2,
                         x1 - ux * tip + uy * tip / 2, y1 - uy * tip - ux * tip / 2])

    def _draw(self, *args):
        self.canvas.clear()
        value = self.measurement.number
        kind = self.measurement.renderer
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        with self.canvas:
            Color(.97, .985, .99, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(24)])
            if kind == 'direction':
                radius = max(dp(15), min(self.width, self.height) / 2 - dp(38))
                Color(*PALE)
                Line(circle=(cx, cy, radius), width=dp(8))
                for angle in range(0, 360, 5):
                    ux, uy, _ = direction_geometry(angle)
                    major = angle % 30 == 0
                    inner = radius - dp(12 if major else 4)
                    Color(*MUTED)
                    Line(points=[cx + inner * ux, cy + inner * uy,
                                 cx + radius * ux, cy + radius * uy], width=dp(1.2 if major else .6))
                for text, x, y in [('N', cx, cy + radius + dp(20)),
                                   ('S', cx, cy - radius - dp(20)),
                                   ('E', cx + radius + dp(20), cy),
                                   ('O', cx - radius - dp(20), cy)]:
                    self._text(text, x, y, 16)
                ux, uy, _ = direction_geometry(indicator_angle(value, self.progress, compass=True))
                self._arrow(cx, cy, cx + ux * radius * .8, cy + uy * radius * .8)
                Ellipse(pos=(cx-dp(5), cy-dp(5)), size=(dp(10), dp(10)))
            elif kind in ('pitch', 'roll'):
                radius = max(dp(12), min(self.width, self.height) / 2 - dp(36))
                Color(*PALE)
                Line(circle=(cx, cy, radius), width=dp(5))
                if self._equipment_texture is not None:
                    texture = self._equipment_texture
                    width, height = fitted_image_size(texture.size, (radius*1.65, radius*1.65))
                    Color(1, 1, 1, 1)
                    Rectangle(texture=texture, pos=(cx-width/2, cy-height/2), size=(width, height))
                # The photograph is context only. The overlay displays the signed
                # angle in the named plane, without inferring the sensor mounting.
                Color(*MUTED[:3], .38)
                Line(points=[cx-radius, cy, cx+radius, cy], width=dp(.65), dash_length=dp(5))
                self._text('0°', cx+radius-dp(4), cy+dp(16), 12)
                ux, uy = inclination_geometry(value, self.progress)
                length = radius * .9
                points = [cx-length*ux, cy-length*uy, cx+length*ux, cy+length*uy]
                # White underlay keeps the functional indicator readable over
                # both the white transducer head and the dark instrument body.
                Color(1, 1, 1, .95)
                Line(points=points, width=dp(5), cap='round')
                Color(*ACCENT)
                Line(points=points, width=dp(2.5), cap='round')
                if kind == 'pitch':
                    self._arrow(cx, cy, cx+length*ux, cy+length*uy)
                else:
                    # Transverse balance beam: end caps rotate with the signed
                    # angle; Pitch retains its longitudinal arrow instead.
                    for sign in (-1, 1):
                        ex, ey = cx+sign*length*ux, cy+sign*length*uy
                        cap = dp(11)
                        endpoints = [ex-cap*uy, ey+cap*ux, ex+cap*uy, ey-cap*ux]
                        Color(1, 1, 1, .95)
                        Line(points=endpoints, width=dp(4), cap='round')
                        Color(*ACCENT)
                        Line(points=endpoints, width=dp(2), cap='round')
                Ellipse(pos=(cx-dp(5), cy-dp(5)), size=(dp(10), dp(10)))
                self._text('frente / trás' if kind == 'pitch' else 'esq. / dir.',
                           cx, self.top-dp(17), 12)
                self._text('Pitch • longitudinal' if kind == 'pitch' else 'Roll • lateral',
                           cx, self.y+dp(18), 14)
            elif kind == 'level':
                ticks = measurement_ticks(self.measurement)
                low, high = ticks[0], ticks[-1]
                x = self.x + self.width * .43
                bottom, top = self.y + dp(28), self.top - dp(28)
                Color(*PALE)
                RoundedRectangle(pos=(x-dp(6), bottom), size=(dp(12), top-bottom), radius=[dp(4)])
                for tick, label in zip(ticks, tick_labels(ticks)):
                    y = bottom + (top - bottom) * (tick-low)/(high-low)
                    Color(*MUTED)
                    Line(points=[x - dp(8), y, x + dp(8), y], width=1)
                    self._text(label, x - dp(46), y)
                fraction = (value-low)/(high-low)
                y = bottom + fraction * self.progress * (top-bottom)
                self._arrow(x + dp(54), y, x + dp(14), y)
                Ellipse(pos=(x-dp(5), y-dp(5)), size=(dp(10), dp(10)))
            elif kind in ('speed', 'battery'):
                ticks = measurement_ticks(self.measurement)
                low, high = ticks[0], ticks[-1]
                x, width = self.x + dp(32), max(dp(20), self.width-dp(64))
                height = dp(64 if kind == 'battery' else 24)
                Color(*PALE)
                RoundedRectangle(pos=(x, cy-height/2), size=(width, height), radius=[dp(8)])
                fraction = (value-low)/(high-low) * self.progress
                Color(*ACCENT)
                if kind == 'battery':
                    Line(rounded_rectangle=(x-dp(5), cy-height/2-dp(5), width+dp(10), height+dp(10), dp(10)), width=dp(1.5))
                    Rectangle(pos=(x+width+dp(5), cy-dp(10)), size=(dp(6), dp(20)))
                if fraction > 0:
                    RoundedRectangle(pos=(x, cy-height/2), size=(width*fraction, height),
                                     radius=[min(dp(8), width*fraction/2)])
                labels = tick_labels(ticks)
                if kind == 'speed':
                    for tick, label in zip(ticks[1:-1], labels[1:-1]):
                        tick_x = x + width * (tick-low)/(high-low)
                        Color(*MUTED)
                        Line(points=[tick_x, cy-height/2-dp(4), tick_x, cy-height/2-dp(9)], width=1)
                        self._text(label, tick_x, cy-height/2-dp(25), 12)
                self._text(labels[0], x, cy-height/2-dp(25))
                self._text(labels[-1], x+width, cy-height/2-dp(25))
                marker_x = x+width*fraction
                Color(*ACCENT)
                Line(points=[marker_x, cy-height/2-dp(5), marker_x, cy+height/2+dp(5)], width=dp(2))
                Ellipse(pos=(marker_x-dp(4), cy+height/2+dp(6)), size=(dp(8), dp(8)))
            elif kind == 'rain':
                # Precipitation symbol, not a capacity gauge or a rainfall rate.
                Color(*PALE)
                Ellipse(pos=(cx-dp(64), cy+dp(5)), size=(dp(72), dp(58)))
                Ellipse(pos=(cx-dp(22), cy+dp(22)), size=(dp(78), dp(64)))
                RoundedRectangle(pos=(cx-dp(60), cy), size=(dp(124), dp(42)), radius=[dp(20)])
                Color(*ACCENT)
                Line(points=[cx-dp(66), cy-dp(72), cx-dp(66), cy-dp(84),
                             cx+dp(66), cy-dp(84), cx+dp(66), cy-dp(72)], width=dp(2))
                if value > 0:
                    Color(*ACCENT[:3], self.progress)
                    for offset in (-36, 0, 36):
                        Line(points=[cx+dp(offset+4), cy-dp(22), cx+dp(offset-4), cy-dp(44)],
                             width=dp(2.5), cap='round')
                else:
                    self._text('0 mm' if value == 0 else 'Valor informado', cx, cy-dp(38), 18)
            elif kind in ('wave_height', 'wave_period'):
                x, width = self.x+dp(32), max(dp(20), self.width-dp(64))
                amplitude = dp(45)
                points = []
                for i in range(121):
                    points.extend((x+width*i/120, cy+amplitude*sin(4*pi*i/120)))
                Color(*PALE)
                Line(points=[x, cy, x+width, cy], width=1)
                Color(*ACCENT)
                Color(*ACCENT[:3], self.progress)
                Line(points=points, width=dp(3))
                if kind == 'wave_height':
                    self._arrow(cx, cy-dp(45), cx, cy+dp(45))
                else:
                    self._arrow(x+width/8, cy+dp(68), x+width*5/8, cy+dp(68))
                self._text('Altura' if kind == 'wave_height' else 'Período', cx, cy-dp(85))
            else:
                # Neutral vector symbol for unsupported or missing measurements.
                Color(*PALE)
                Ellipse(pos=(cx-dp(60), cy-dp(60)), size=(dp(120), dp(120)))
                Color(*ACCENT)
                for i, height in enumerate((25, 52, 38)):
                    RoundedRectangle(pos=(cx-dp(32)+dp(24)*i, cy-dp(26)),
                                     size=(dp(14), dp(height)), radius=[dp(5)])


def detail_renderer(measurement):
    return MeasurementGraphic(measurement)


def text_label(text, height, size, color=INK):
    widget = Label(text=text, color=color, size_hint_y=None, height=dp(height),
                   font_size=sp(size), halign='center', valign='middle')
    widget.bind(size=lambda instance, dimensions: setattr(instance, 'text_size', dimensions))
    return widget


class MeasurementPage(ScrollView):
    def __init__(self, measurement, **kwargs):
        super().__init__(do_scroll_x=False, **kwargs)
        body = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))
        body.add_widget(text_label(measurement.name, 48, 23))
        body.add_widget(text_label(measurement.display_value if measurement.number is not None else 'Sem dado', 76, 48))
        body.add_widget(text_label(measurement.unit, 28, 20, MUTED))
        self.graphic = detail_renderer(measurement)
        self.graphic.size_hint_y = None
        self.graphic.height = dp(264)
        body.add_widget(self.graphic)
        kind = measurement.renderer
        caption = ''
        if kind == 'direction':
            caption = direction_geometry(measurement.number)[2] + ' • Norte = 0°'
        elif kind in ('pitch', 'roll'):
            caption = 'Ângulo informado • referência horizontal = 0°'
        elif kind in ('speed', 'level', 'battery'):
            caption = 'Escala visual automática • sem limites operacionais'
            if kind == 'battery':
                caption = ('Carga informada pelo equipamento' if measurement.unit.strip() == '%' and 0 <= measurement.number <= 100
                           else 'Escala visual automática • não indica % de carga')
        elif kind == 'rain':
            caption = 'Precipitação informada pelo equipamento'
        elif kind in ('wave_height', 'wave_period'):
            caption = 'Esquema ilustrativo • sem dados históricos'
        body.add_widget(text_label(caption, 48, 13, MUTED))
        body.add_widget(text_label('Registro: ' + friendly_timestamp(measurement.timestamp), 32, 14, MUTED))
        self.add_widget(body)


class MeasurementDetailModal(ModalView):
    def __init__(self, measurements, initial_index=0, **kwargs):
        # Retain the single-measurement entry point for existing callers.
        if isinstance(measurements, Measurement):
            measurements = (measurements,)
        self.measurements = tuple(measurements)
        if not self.measurements or not 0 <= initial_index < len(self.measurements):
            raise ValueError('Viewer requires measurements and a valid initial index')
        if any(m.origin != self.measurements[0].origin for m in self.measurements):
            raise ValueError('Viewer must contain only one equipment')
        self._viewer_open = False
        super().__init__(size_hint=(1, 1), background='', background_color=(1, 1, 1, 1),
                         auto_dismiss=True, **kwargs)
        app = App.get_running_app()
        top, bottom = getattr(app, 'safe_top', 0), getattr(app, 'safe_bottom', 0)
        root = BoxLayout(orientation='vertical', padding=[dp(20), top+dp(12), dp(20), bottom+dp(12)], spacing=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        origin = text_label(self.measurements[0].origin or 'Equipamento', 56, 20)
        origin.halign = 'left'
        header.add_widget(origin)
        close = Button(text='Fechar', size_hint=(None, 1), width=dp(68),
                       background_normal='', background_color=(0, 0, 0, 0), color=ACCENT, font_size=sp(14))
        close.bind(on_release=self.dismiss)
        header.add_widget(close)
        root.add_widget(header)
        self.carousel = Carousel(direction='right', loop=False, ignore_perpendicular_swipes=True,
                                 scroll_distance=dp(12), anim_move_duration=.22, anim_cancel_duration=.15)
        for measurement in self.measurements:
            self.carousel.add_widget(MeasurementPage(measurement))
        self.carousel.index = initial_index
        self.counter = text_label('', 32, 14, MUTED)
        root.add_widget(self.carousel)
        root.add_widget(self.counter)
        self.add_widget(root)
        self.carousel.bind(index=self._page_changed)
        self._page_changed()

    def _page_changed(self, *args):
        index = self.carousel.index or 0
        count = len(self.measurements)
        self.counter.text = f'{index+1} de {count}' + ('  •  Deslize para navegar' if count > 1 else '')
        for page in self.carousel.slides:
            page.graphic.stop()
        if self._viewer_open:
            self.carousel.slides[index].graphic.animate()

    def on_open(self):
        self._viewer_open = True
        self._page_changed()

    def on_pre_dismiss(self):
        self._viewer_open = False
        for page in self.carousel.slides:
            page.graphic.stop()
