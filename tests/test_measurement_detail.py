"""Snapshot, renderer and tap routing checks without Kivy or backend calls."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from measurement_model import (Measurement, direction_geometry, visual_scale, equipment_snapshot,
                               friendly_timestamp, scale_ticks, tick_labels, measurement_ticks,
                               indicator_angle, inclination_geometry, fitted_image_size)
from test_directional_scrollview import load_view, Touch, VerticalParent

ROOT = Path(__file__).resolve().parents[1]


def sample(name='Maré Reduzida', value=1.25):
    return Measurement(name, value, str(value), 'm', 'res/logo.png', 'Marégrafo', '2026-09-30 12:00')


def methods(path, cls_name, names):
    tree = ast.parse((ROOT / path).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
    return [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]


class MeasurementTests(unittest.TestCase):
    def test_renderer_types(self):
        for name, kind in [('Maré Reduzida', 'level'), ('Dir. Corr.', 'direction'),
                           ('Dir. Vento', 'direction'), ('Vel. Corr.', 'speed'),
                           ('Vel. Vento', 'speed'), ('Rajada', 'speed'),
                           ('Bateria', 'battery'), ('Altura Onda', 'wave_height'),
                           ('Período Onda', 'wave_period'), ('Pitch', 'pitch'), ('Roll', 'roll'), ('Chuva', 'rain')]:
            with self.subTest(name=name):
                self.assertEqual(sample(name).renderer, kind)

    def test_generic_fallback(self):
        for name, kind in [('Bateria', 'battery'), ('Altura Onda', 'wave_height'),
                           ('Período Onda', 'wave_period'), ('Desconhecida', 'generic')]:
            self.assertEqual(sample(name).visual_type, kind)
            self.assertEqual(sample(name).renderer, kind)
        for value in [None, '-', 'NaN', float('inf'), True]:
            self.assertEqual(sample(value=value).renderer, 'generic')

    def test_actual_renderer_factory(self):
        tree = ast.parse((ROOT / 'measurement_detail.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'detail_renderer')
        ns = {'Image': Mock(), 'MeasurementGraphic': Mock()}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'factory', 'exec'), ns)
        for measurement in [sample(), sample('Dir. Vento'), sample('Vel. Corr.')]:
            ns['detail_renderer'](measurement)
            ns['MeasurementGraphic'].assert_called_with(measurement)
        ns['detail_renderer'](sample('Bateria'))
        ns['MeasurementGraphic'].assert_called_with(sample('Bateria'))
        ns['Image'].assert_not_called()

    def test_exact_direction_and_scale_positions(self):
        x, y, cardinal = direction_geometry(90)
        self.assertAlmostEqual(x, 1)
        self.assertAlmostEqual(y, 0)
        self.assertEqual(cardinal, 'E')
        self.assertEqual(direction_geometry(360)[2], 'N')
        self.assertEqual(direction_geometry(225)[2], 'SO')
        for value in [-2.3, 0, .01, 12.345]:
            for kind in ['level', 'speed']:
                low, high = visual_scale(value, kind)
                self.assertLess(high - low, float('inf'))
                self.assertLessEqual(low, value)
                self.assertGreaterEqual(high, value)

    def test_readable_scale_limits_and_regular_ticks(self):
        for value, kind, expected in [(7.68, 'speed', 10), (10.02, 'speed', 12.5),
                                      (12.60, 'battery', 15)]:
            self.assertEqual(visual_scale(value, kind), (0, expected))
        for value in [-12.6, -.84, 0, .001, .84, 12.6]:
            ticks = scale_ticks(value, 'level')
            self.assertLessEqual(ticks[0], value)
            self.assertGreaterEqual(ticks[-1], value)
            step = ticks[1]-ticks[0]
            for a, b in zip(ticks, ticks[1:]):
                self.assertAlmostEqual(b-a, step)
        self.assertEqual(tick_labels(scale_ticks(.84, 'level')),
                         ('0.0', '0.5', '1.0', '1.5'))

    def test_adcp_asset_and_image_fit(self):
        import struct
        asset = ROOT / 'res/equipamentos/nortek_awac.png'
        header = asset.read_bytes()[:24]
        self.assertEqual(header[:8], b'\x89PNG\r\n\x1a\n')
        native = struct.unpack('>II', header[16:24])
        self.assertEqual(fitted_image_size(native, (1000, 1000)), native)
        self.assertEqual(fitted_image_size((300, 300), (120, 200)), (120, 120))
        self.assertEqual(fitted_image_size((300, 150), (100, 100)), (100, 50))

    def test_pitch_and_roll_draw_distinct_orientation_overlays(self):
        from contextlib import nullcontext
        functions = methods('measurement_detail.py', 'MeasurementGraphic', {'_draw'})
        ns = dict(dp=lambda v: v, PALE=(1, 1, 1, 1), MUTED=(.4, .4, .4, 1),
                  ACCENT=(0, .5, .6, 1), inclination_geometry=inclination_geometry,
                  fitted_image_size=fitted_image_size)
        for name in ('Color', 'Line', 'Rectangle', 'RoundedRectangle', 'Ellipse'):
            ns[name] = Mock()
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'drawing', 'exec'), ns)
        for kind, hint in [('Pitch', 'frente / trás'), ('Roll', 'esq. / dir.')]:
            canvas = nullcontext()
            canvas.clear = Mock()
            graphic = SimpleNamespace(canvas=canvas, measurement=sample(kind, 20),
                                      x=0, y=0, width=350, height=264, top=264, progress=1,
                                      pos=(0, 0), size=(350, 264),
                                      _equipment_texture=SimpleNamespace(size=(300, 300)),
                                      _text=Mock(), _arrow=Mock())
            ns['Line'].reset_mock()
            ns['_draw'](graphic)
            graphic._text.assert_any_call(hint, 175, 247, 12)
            if kind == 'Pitch':
                graphic._arrow.assert_called_once()
                pitch_lines = ns['Line'].call_count
            else:
                graphic._arrow.assert_not_called()
                self.assertEqual(ns['Line'].call_count, pitch_lines+4)
            size = ns['Rectangle'].call_args.kwargs['size']
            self.assertAlmostEqual(size[0]/(96*1.4), 1.65/1.4)
            self.assertLessEqual(size[0], 300)

    def test_pitch_roll_sign_zero_and_final_angle(self):
        for name in ('Pitch', 'Roll'):
            for value in (-30, 0, 30):
                measurement = sample(name, value)
                self.assertEqual(measurement.renderer, name.lower())
                x, y = inclination_geometry(value)
                self.assertAlmostEqual(x, 1 if value == 0 else 3**.5/2)
                self.assertAlmostEqual(y, value/60)
                self.assertEqual(inclination_geometry(value, 0), (1, 0))
                self.assertEqual(indicator_angle(value, 1), value)
                self.assertEqual(measurement.number, value)

    def test_compass_shortest_path_preserves_final_cardinal(self):
        self.assertEqual(indicator_angle(350, .5, compass=True), -5)
        for angle in (0, 45, 90, 180, 225, 350, 360, -10):
            final = indicator_angle(angle, 1, compass=True)
            self.assertLessEqual(abs(final), 180)
            self.assertEqual(direction_geometry(final), direction_geometry(angle))

    def test_weather_renderers_and_zero_rain(self):
        for name, kind in [('Vel. Vento', 'speed'), ('Rajada', 'speed'),
                           ('Dir. Vento', 'direction'), ('Chuva', 'rain')]:
            for value in (0, 7.68):
                self.assertEqual(sample(name, value).renderer, kind)
        rain = Measurement('Chuva', 0, '0.00', 'mm', '', 'Estação', '')
        self.assertEqual(rain.display_value, '0.00')
        self.assertEqual(rain.number, 0)
        self.assertEqual(sample('Chuva', None).renderer, 'generic')

    def test_voltage_scale_is_not_charge_percent(self):
        battery = Measurement('Bateria', 12.6, '12.60', 'V', '', 'Boia', '')
        self.assertEqual(measurement_ticks(battery)[-1], 15)
        self.assertEqual(battery.unit, 'V')
        self.assertEqual(battery.display_value, '12.60')
        percent = Measurement('Bateria', 65, '65', '%', '', 'Boia', '')
        self.assertEqual(measurement_ticks(percent)[-1], 100)

    def test_animation_completion_and_stop_preserve_measurement(self):
        functions = methods('measurement_detail.py', 'MeasurementGraphic', {'animate', 'stop'})
        animation = Mock()
        ns = {'Animation': animation}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'animation', 'exec'), ns)
        for name in ('Pitch', 'Roll', 'Dir. Vento', 'Maré Reduzida', 'Bateria', 'Chuva', 'Vel. Vento', 'Rajada'):
            measurement = sample(name, 12.6)
            graphic = SimpleNamespace(measurement=measurement, progress=1)
            ns['animate'](graphic)
            self.assertEqual(graphic.progress, 0)
            kwargs = animation.call_args.kwargs
            self.assertEqual(kwargs['progress'], 1)
            self.assertLessEqual(kwargs['duration'], .5)
            graphic.progress = kwargs['progress']
            self.assertIs(graphic.measurement, measurement)
            ns['stop'](graphic)
            self.assertEqual(graphic.progress, 1)
            self.assertEqual(measurement.number, 12.6)

    def test_snapshot_keeps_origin_timestamp_and_precision(self):
        measurement = sample(value=1.234567)
        self.assertEqual(measurement.number, 1.234567)
        self.assertEqual(measurement.origin, 'Marégrafo')
        self.assertEqual(measurement.timestamp, '2026-09-30 12:00')


    def test_equipment_snapshot_preserves_order_and_initial_index(self):
        first, selected, last = sample('Bateria'), sample('Dir. Vento'), sample('Chuva')
        other = Measurement('Bateria', 12, '12', 'V', '', 'Outro', '')
        group, index = equipment_snapshot([first, other, selected, last], selected)
        self.assertEqual(group, (first, selected, last))
        self.assertEqual(index, 1)
        self.assertIs(group[index], selected)

    def test_refresh_does_not_replace_tapped_value(self):
        selected = sample(value=1.2)
        self.assertEqual(equipment_snapshot([sample(value=1.3)], selected), ((selected,), 0))

    def test_timestamp_preserves_local_time_and_invalid_text(self):
        for value in ['2026-09-30 12:35:00.0', '2026-09-30T12:35:00-03:00']:
            self.assertEqual(friendly_timestamp(value), '30/09/2026 12:35')
        self.assertEqual(friendly_timestamp('invalid'), 'invalid')
        self.assertEqual(friendly_timestamp(''), 'Não informado')

    def test_navigation_updates_counter_and_only_animates_current_page(self):
        functions = methods('measurement_detail.py', 'MeasurementDetailModal',
                            {'_page_changed', 'on_open', 'on_pre_dismiss'})
        ns = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'viewer', 'exec'), ns)
        pages = [SimpleNamespace(graphic=Mock()) for _ in range(3)]
        modal = SimpleNamespace(carousel=SimpleNamespace(index=1, slides=pages),
                                measurements=(sample(),)*3, counter=SimpleNamespace(text=''),
                                _viewer_open=False)
        modal._page_changed = lambda: ns['_page_changed'](modal)
        ns['on_open'](modal)
        self.assertTrue(modal.counter.text.startswith('2 de 3'))
        pages[1].graphic.animate.assert_called_once()
        pages[0].graphic.animate.assert_not_called()
        modal.carousel.index = 2
        modal._page_changed()
        self.assertTrue(modal.counter.text.startswith('3 de 3'))
        pages[2].graphic.animate.assert_called_once()
        ns['on_pre_dismiss'](modal)
        self.assertFalse(modal._viewer_open)
        calls = pages[2].graphic.animate.call_count
        modal._page_changed()
        self.assertEqual(pages[2].graphic.animate.call_count, calls)
        ns['on_open'](modal)
        self.assertEqual(pages[2].graphic.animate.call_count, calls+1)

    def test_worker_uses_the_timestamp_of_each_measurement(self):
        rows = [dict(TmStamp='2026-09-30 12:35:00.0', dir11=47.5123),
                dict(TmStamp='2026-09-30 12:40:00.0', PNORW_Hm0=1.2345)]
        app = SimpleNamespace(selected_parameters={'Boia 08': ['Dir. Corr.', 'Altura Onda']})
        ns = dict(MDApp=SimpleNamespace(get_running_app=lambda: app),
                  api_ultimosDados=lambda: {'ok': True}, Clock=Mock(), datetime=datetime,
                  PARAMETROS_IMAGENS={'Dir. Corr.': 'direction.png', 'Altura Onda': 'wave.png'},
                  UNIDADES_MEDIDA={'Dir. Corr.': '°', 'Altura Onda': 'm'}, Measurement=Measurement)
        function = methods('main.py', 'Overview', {'_generate_cards_threaded'})
        exec(compile(ast.Module(body=function, type_ignores=[]), 'worker', 'exec'), ns)
        overview = SimpleNamespace(card_configs=[{'text': 'Boia 08'}],
                                   identifica_e_retorna_dados=lambda **kwargs: rows,
                                   dicionario_parametros={'Dir. Corr.': 'dir11', 'Altura Onda': 'PNORW_Hm0'},
                                   _update_ui=Mock())
        ns['_generate_cards_threaded'](overview)
        ns['Clock'].schedule_once.call_args.args[0](0)
        card = overview._update_ui.call_args.args[0][0]
        direction = card['imagens_dados'][0][3]
        wave = card['imagens_dados'][1][3]
        self.assertEqual(direction.timestamp, rows[0]['TmStamp'])
        self.assertEqual(wave.timestamp, rows[1]['TmStamp'])
        self.assertEqual(direction.number, 47.5123)
        self.assertEqual(direction.display_value, '47.51')
        self.assertEqual(wave.origin, 'Boia 08')


class DetailTapTests(unittest.TestCase):
    def setUp(self):
        self.view, self.clock = load_view()
        self.parent = VerticalParent(self.view)
        ns = {'MeasurementDetailModal': Mock(), 'Logger': Mock(),
              'equipment_snapshot': equipment_snapshot, 'Animation': Mock()}
        functions = methods('main.py', 'Overview', {'open_measurement', '_measurement_closed'})
        functions += methods('measurement_detail.py', 'MeasurementTile', {'on_release'})
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'callbacks', 'exec'), ns)
        self.ns = ns
        self.overview = SimpleNamespace(_measurement_detail=None)
        self.overview._measurement_closed = lambda instance: ns['_measurement_closed'](self.overview, instance)
        self.measurement = sample()
        self.tile = SimpleNamespace(measurement=self.measurement,
                                    open_detail=lambda m: ns['open_measurement'](self.overview, m))
        # Nested ScrollView synthesizes down/up only for a tap. Simulate the
        # ButtonBehavior release delivered at the end of that sequence.
        self.view._do_touch_up.side_effect = lambda *args: ns['on_release'](self.tile)

    def finish(self, offsets):
        touch = Touch()
        self.parent.down(touch)
        for dx, dy in offsets:
            touch.move(dx, dy)
            self.parent.move(touch)
        self.parent.up(touch)
        for call in self.clock.schedule_once.call_args_list:
            call.args[0](0)

    def test_tap_opens_snapshot(self):
        self.finish([(2, 1)])
        self.ns['MeasurementDetailModal'].assert_called_once_with((self.measurement,), initial_index=0)
        self.ns['MeasurementDetailModal'].return_value.open.assert_called_once()


    def test_tap_passes_same_equipment_group_and_selected_index(self):
        first = sample('Bateria')
        other = Measurement('Chuva', 1, '1', 'mm', '', 'Outro', '')
        self.overview.cards_data = [
            {'imagens_dados': [('', '', '', first), ('', '', '', self.measurement)]},
            {'imagens_dados': [('', '', '', other)]}]
        self.finish([])
        self.ns['MeasurementDetailModal'].assert_called_once_with(
            (first, self.measurement), initial_index=1)

    def test_drag_never_opens_detail(self):
        for offsets in [[(12, 0)], [(0, 12)], [(12, 9)], [(9, 12)],
                        [(12, 12)], [(12, 12), (0, 0)]]:
            with self.subTest(offsets=offsets):
                self.setUp()
                self.finish(offsets)
                self.ns['MeasurementDetailModal'].assert_not_called()

    def test_no_duplicate_modal_and_reopen_after_close(self):
        self.finish([])
        self.ns['on_release'](self.tile)
        self.ns['MeasurementDetailModal'].assert_called_once()
        self.overview._measurement_closed(self.overview._measurement_detail)
        self.ns['on_release'](self.tile)
        self.assertEqual(self.ns['MeasurementDetailModal'].call_count, 2)

    def test_modal_failure_does_not_block_next_tap(self):
        self.ns['MeasurementDetailModal'].side_effect = RuntimeError()
        self.finish([])
        self.assertIsNone(self.overview._measurement_detail)


if __name__ == '__main__':
    unittest.main()
