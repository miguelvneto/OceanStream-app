"""Snapshot, renderer and tap routing checks without Kivy or backend calls."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from measurement_model import Measurement, direction_geometry, visual_scale, equipment_snapshot, friendly_timestamp
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
                           ('Período Onda', 'wave_period')]:
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
