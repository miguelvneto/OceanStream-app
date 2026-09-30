"""Navigation decisions and native adapter contracts, without a mobile build."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock

from system_navigation import remaining_insets, android_insets, ios_insets, back_action, request_safe_area

ROOT = Path(__file__).resolve().parents[1]


def app_methods(names, namespace):
    tree = ast.parse((ROOT / 'main.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OceanStream')
    body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=body, type_ignores=[]), 'app_methods', 'exec'), namespace)
    return namespace


class InsetsTests(TestCase):
    def test_edge_to_edge_and_fitted_surface(self):
        self.assertEqual(remaining_insets(24, 34, 0, 0, 800, 1600), (48, 68))
        self.assertEqual(remaining_insets(24, 34, 24, 34, 742, 1484), (0, 0))
        self.assertEqual(remaining_insets(24, 34, 24, 10, 766, 766), (0, 24))
        # A keyboard-resized surface must not add its height as a system inset.
        self.assertEqual(remaining_insets(24, 34, 24, 300, 476, 476), (0, 0))

    def test_invalid_geometry(self):
        for height in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                remaining_insets(24, 34, 0, 0, height, 800)

    def test_android_native_gesture_and_three_button_insets(self):
        for bottom in (24, 48):
            decor, surface, insets = Mock(), Mock(), Mock()
            decor.getHeight.return_value = 800
            surface.getHeight.return_value = 800
            decor.getRootWindowInsets.return_value = insets
            insets.getInsets.return_value = NS(top=24, bottom=bottom)
            for view in (decor, surface):
                view.getLocationOnScreen.side_effect = lambda position: position.__setitem__(slice(None), [0, 0])
            types = NS(systemBars=lambda: 1, displayCutout=lambda: 2,
                       mandatorySystemGestures=lambda: 4)
            classes = {'android.os.Build$VERSION': NS(SDK_INT=35), 'android.view.WindowInsets$Type': types}
            activity = Mock()
            activity.getWindow.return_value.getDecorView.return_value = decor
            activity.getSurface.return_value = surface
            self.assertEqual(android_insets(activity, classes.__getitem__, 800), (24, bottom))
            insets.getInsets.assert_called_once_with(7)

    def test_ios_safe_layout_uses_view_coordinates_and_scale(self):
        rect = lambda y, height: NS(origin=NS(y=y), size=NS(height=height))
        view = Mock()
        view.bounds.return_value = rect(0, 844)
        view.safeAreaLayoutGuide.return_value.layoutFrame.return_value = rect(47, 763)
        window = Mock()
        window.isKeyWindow.return_value = True
        window.rootViewController.return_value.view.return_value = view
        app = Mock()
        app.windows.return_value.count.return_value = 1
        app.windows.return_value.objectAtIndex_.return_value = window
        objc = Mock()
        objc.return_value.sharedApplication.return_value = app
        self.assertEqual(ios_insets(objc, 1688), (94, 68))
        view.safeAreaLayoutGuide.return_value.layoutFrame.return_value = rect(0, 844)
        self.assertEqual(ios_insets(objc, 1688), (0, 0))

    def test_desktop_requires_no_native_bridge(self):
        callback = Mock()
        request_safe_area('linux', 800, callback)
        callback.assert_called_once_with((0, 0))

    def test_stale_insets_and_transient_failure(self):
        ns = app_methods({'_apply_safe_area'}, {'Logger': Mock()})
        app = NS(_safe_area_generation=2, safe_top=0, safe_bottom=0,
                 navigation_bar=NS(bottom_inset=0), _fallback_safe_area=Mock())
        ns['_apply_safe_area'](app, 1, (10, 20))
        self.assertEqual(app.safe_bottom, 0)
        ns['_apply_safe_area'](app, 2, (47, 34))
        self.assertEqual(app.navigation_bar.bottom_inset, 34)
        ns['_apply_safe_area'](app, 2, None)
        self.assertEqual(app.safe_bottom, 34)
        app._fallback_safe_area.assert_not_called()

    def test_toolbar_expands_above_safe_area(self):
        tree = ast.parse((ROOT / 'navigation_bar.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_position_above_system')
        ns = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'bar', 'exec'), ns)
        bar = NS(toolbar=NS(height=56), bottom_inset=34)
        for height in (56, 100, 206):
            bar.toolbar.height = height
            ns['_position_above_system'](bar)
            self.assertEqual((bar.y, bar.height), (34, height))


class BackTests(TestCase):
    def test_overview_delegates_and_internal_screens_return(self):
        self.assertIsNone(back_action('android', 27, 'overview'))
        self.assertIsNone(back_action('android', 27, 'login'))
        for screen in ('configuracao', 'equipamento'):
            self.assertEqual(back_action('android', 27, screen), 'overview')
            self.assertIsNone(back_action('android', 27, screen, blocked=True))
        self.assertEqual(back_action('android', 27, 'equipamento', drawer_open=True), 'close_drawer')
        self.assertIsNone(back_action('ios', 27, 'equipamento'))
        self.assertIsNone(back_action('android', 28, 'equipamento'))

    def test_app_handler_preserves_session_and_modal_priority(self):
        class Modal:
            pass
        window = NS(keyboard_height=0, children=[])
        ns = app_methods({'_system_back'}, {'Window': window, 'ModalView': Modal,
                                          'platform': 'android', 'back_action': back_action})
        screen = NS(name='overview', walk=lambda: [], _drawer_open=False, close_equipment_drawer=Mock())
        app = NS(gerenciador=NS(current_screen=screen, current='overview'),
                 logout=Mock(), token='unchanged')
        self.assertFalse(ns['_system_back'](app, window, 27))
        screen.name = 'equipamento'
        window.children = [Modal()]
        self.assertFalse(ns['_system_back'](app, window, 27))
        window.children = []
        window.keyboard_height = 200
        self.assertFalse(ns['_system_back'](app, window, 27))
        window.keyboard_height = 0
        screen._drawer_open = True
        self.assertTrue(ns['_system_back'](app, window, 27))
        screen.close_equipment_drawer.assert_called_once()
        screen._drawer_open = False
        self.assertTrue(ns['_system_back'](app, window, 27))
        self.assertEqual(app.gerenciador.current, 'overview')
        app.logout.assert_not_called()
        self.assertEqual(app.token, 'unchanged')

    def test_resume_only_refreshes_geometry(self):
        clock = Mock()
        ns = app_methods({'on_resume'}, {'Clock': clock})
        app = NS(_update_safe_area=Mock(), logout=Mock(), token='unchanged')
        ns['on_resume'](app)
        app._update_safe_area.assert_called_once()
        app.logout.assert_not_called()
        self.assertEqual(app.token, 'unchanged')
        clock.schedule_once.assert_called_once_with(app._update_safe_area, .5)
