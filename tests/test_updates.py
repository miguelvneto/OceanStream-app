"""Testes sem Kivy, rede ou navegador; callbacks reais extraídos via AST."""
import ast
import configparser
import re
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import app_version
from update_utils import normalize_version, parse_version_response, store_urls, tem_atualizacao

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / 'main.py').read_text())


def load_callbacks():
    names = {'check_for_updates', '_safe_redirect_to_overview', '_handle_update_result', 'show_update_dialog', '_on_dialog_dismiss',
             '_close_update_dialog', 'open_store', '_redirect_to_overview'}
    methods = [n for cls in TREE.body if isinstance(cls, ast.ClassDef)
               for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    api = next(n for n in TREE.body if isinstance(n, ast.FunctionDef)
               and n.name == 'api_lastestVersion')
    namespace = dict(normalize_version=normalize_version, tem_atualizacao=tem_atualizacao,
                     parse_version_response=parse_version_response, store_urls=store_urls,
                     platform='android', APP_STORE_ID=None, Logger=Mock(), Clock=Mock(),
                     Thread=Mock(), VERSAO_ATUAL='0.4.1', MDApp=Mock(),
                     MDFlatButton=Mock(), MDDialog=Mock(), requests=Mock(),
                     get_access_token=Mock(return_value='test-token'),
                     API_PRFX='https://example.invalid/', HTTP_TIMEOUT=25)
    exec(compile(ast.Module(body=methods + [api], type_ignores=[]), 'callbacks', 'exec'), namespace)
    cls = type('UpdateCallbacks', (), {name: namespace[name] for name in names})
    ui = cls()
    ui.check_for_updates()
    return ui, namespace


class VersionTests(unittest.TestCase):
    def test_comparison(self):
        cases = [('0.4.1', '0.4.1', False), ('0.4.1', '0.4.2', True),
                 ('0.4.1', '0.4.1.1', True), ('0.4.1.1', '0.4.1', False),
                 ('0.4.1', '0.4.1.0', False), ('0.4', '0.4.0', False),
                 ('0.4.2', '0.4.10', True), ('0.4.1', 'v0.4.2', True),
                 ('0.4.1', 'V0.4.2', True), ('0.4.1', '"0.4.2"', True),
                 ('0.4.1', "'0.4.2'", True), ('0.4.1', ' 0.4.2 \n', True)]
        for current, latest, expected in cases:
            with self.subTest(current=current, latest=latest):
                self.assertEqual(tem_atualizacao(current, latest), expected)

    def test_invalid(self):
        for value in ['', ' ', None, 42, 0.4, True, [], {}, '0..2', '-1.2',
                      '0.4.2rc1', '0.4.2+build', '"0.4.2', '0. 4', '١.٢', '9'*257]:
            with self.subTest(value=value):
                self.assertIsNone(normalize_version(value))
                self.assertFalse(tem_atualizacao('0.4.1', value))
                self.assertFalse(tem_atualizacao(value, '0.4.2'))

    def test_api_formats(self):
        for body in ['{"version":"0.4.2"}', '{"latest_version":"0.4.2"}',
                     '"0.4.2"', '0.4.2', ' 0.4.2 ',
                     '{"version":42,"latest_version":"v0.4.2"}']:
            with self.subTest(body=body):
                self.assertEqual(parse_version_response(body), '0.4.2')
        for body in ['{}', '[]', 'null', '42', 'true', '{bad', '<html>error</html>',
                     '{"version":[]}', 'x'*4097, None]:
            self.assertIsNone(parse_version_response(body))

    def test_original_body_and_json_types(self):
        for body, expected in [('0.4', '0.4'), (' 0.4 ', '0.4'),
                               ('0.4.2', '0.4.2'), ('"0.4"', '0.4'),
                               ('"0.4.2"', '0.4.2'),
                               ('{"version":"0.4"}', '0.4')]:
            with self.subTest(body=body):
                self.assertEqual(parse_version_response(body), expected)
        for body in ['42', 'true', 'null', '[0,4]', '{"version":0.4}',
                     '{"latest_version":42}', '4e-1', '0.4e0', 0.4, 42]:
            with self.subTest(body=body):
                self.assertIsNone(parse_version_response(body))

    def test_store_urls(self):
        self.assertEqual(store_urls('android'),
                         ('https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream',))
        for value in [None, '', 123, 'abc', '0', '123/evil', ' 123 ']:
            self.assertEqual(store_urls('ios', value), ())
        self.assertEqual(store_urls('ios', '123456'),
                         ('itms-apps://itunes.apple.com/app/id123456',
                          'https://apps.apple.com/app/id123456'))

    def test_single_version_source(self):
        self.assertEqual(app_version.__version__, "1.6")
        imports = [n for n in TREE.body if isinstance(n, ast.ImportFrom)
                   and n.module == 'app_version']
        self.assertEqual(len(imports), 1)
        self.assertEqual([(n.name, n.asname) for n in imports[0].names],
                         [('__version__', 'VERSAO_ATUAL')])
        namespace = {}
        exec(compile(ast.Module(body=imports, type_ignores=[]), 'version_import', 'exec'),
             namespace)
        self.assertEqual(namespace['VERSAO_ATUAL'], app_version.__version__)
        assignments = [n for n in ast.walk(TREE) if isinstance(n, (ast.Assign, ast.AnnAssign))]
        for node in assignments:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            self.assertFalse(any(isinstance(t, ast.Name) and t.id == 'VERSAO_ATUAL'
                                 for target in targets for t in ast.walk(target)))
        self.assertNotIn('0.4.1', (ROOT / 'main.py').read_text())

    def test_buildozer_reads_single_version_source(self):
        config = configparser.ConfigParser()
        config.read(ROOT / 'buildozer.spec')
        self.assertNotIn('version', config['app'])
        self.assertNotIn('android.numeric_version', config['app'])
        self.assertEqual(config['app']['version.filename'], 'app_version.py')
        source = (ROOT / config['app']['version.filename']).read_text()
        # Buildozer 1.5.0 usa re.search sem flags e o primeiro grupo capturado.
        match = re.search(config['app']['version.regex'], source)
        self.assertIsNotNone(match)
        self.assertEqual(match.groups(), ('1.6',))
        self.assertEqual(match.group(1), app_version.__version__)
        self.assertNotIn('version = 0.3.4', (ROOT / 'buildozer.spec').read_text())
        self.assertIn('tests', config['app']['source.exclude_dirs'].split(','))


class CallbackTests(unittest.TestCase):
    def setUp(self):
        self.ui, self.ns = load_callbacks()

    def test_api_request_and_failures(self):
        request = self.ns['requests'].post
        request.return_value.status_code = 200
        for body in ['{"version":"0.4.2"}', '{"latest_version":"0.4.2"}', '"0.4.2"', '0.4.2']:
            request.return_value.text = body
            self.assertEqual(self.ns['api_lastestVersion'](), '0.4.2')
        self.assertEqual(request.call_args.args[0], 'https://example.invalid/lastestVersion/android')
        self.assertEqual(request.call_args.kwargs['timeout'], 25)
        request.return_value.text = '[]'
        self.assertIsNone(self.ns['api_lastestVersion']())
        request.return_value.status_code = 500
        self.assertIsNone(self.ns['api_lastestVersion']())
        request.side_effect = TimeoutError()
        self.assertIsNone(self.ns['api_lastestVersion']())

    def test_invalid_version_and_missing_ios_id_continue(self):
        self.ui._handle_update_result('0.4.1', {}, 1)
        self.ns['MDDialog'].assert_not_called()
        self.ns['Clock'].schedule_once.assert_called_once()
        self.setUp()
        self.ns['platform'] = 'ios'
        self.ui._handle_update_result('0.4.1', '0.4.2', 1)
        self.ns['MDDialog'].assert_not_called()
        self.ns['Clock'].schedule_once.assert_called_once()

    def test_unexpected_comparison_failure(self):
        self.ns['tem_atualizacao'] = Mock(side_effect=RuntimeError())
        self.ui._handle_update_result('0.4.1', '0.4.2', 1)
        self.ns['Clock'].schedule_once.assert_called_once()

    def test_dialog_failures(self):
        for stage in ['button', 'dialog', 'open']:
            with self.subTest(stage=stage):
                self.setUp()
                target = {'button': self.ns['MDFlatButton'], 'dialog': self.ns['MDDialog'],
                          'open': self.ns['MDDialog'].return_value.open}[stage]
                target.side_effect = RuntimeError()
                self.ui.show_update_dialog('0.4.1', '0.4.2')
                self.ns['Clock'].schedule_once.assert_called_once()

    def test_duplicate_results_do_not_duplicate_dialog(self):
        self.ui._handle_update_result('0.4.1', '0.4.2', 1)
        self.ui._handle_update_result('0.4.1', '0.4.2', 1)
        self.ns['MDDialog'].assert_called_once()

    def test_old_response_ignored_after_new_check(self):
        old_id = self.ui._update_request_id
        self.ui.check_for_updates()
        new_id = self.ui._update_request_id
        self.assertNotEqual(old_id, new_id)
        self.ui._handle_update_result('0.4.1', '0.4.2', old_id)
        self.ns['MDDialog'].assert_not_called()
        self.ns['Clock'].schedule_once.assert_not_called()
        self.ui._handle_update_result('0.4.1', '0.4.2', new_id)
        self.ns['MDDialog'].assert_called_once()

    def test_late_response_after_dismiss_does_not_reopen(self):
        request_id = self.ui._update_request_id
        self.ui._handle_update_result('0.4.1', '0.4.2', request_id)
        self.ui._on_dialog_dismiss(self.ui.dialog)
        self.ui._handle_update_result('0.4.1', '0.4.2', request_id)
        self.ns['MDDialog'].assert_called_once()
        self.ns['Clock'].schedule_once.assert_called_once()

    def test_later_legitimate_check_still_works(self):
        self.ui._handle_update_result('0.4.1', '0.4.2', self.ui._update_request_id)
        self.ui._redirect_to_overview()
        self.ui.check_for_updates()
        request_id = self.ui._update_request_id
        self.ui._handle_update_result('0.4.1', '0.4.2', request_id)
        self.ui._handle_update_result('0.4.1', '0.4.2', request_id)
        self.ui._redirect_to_overview()
        self.ui._redirect_to_overview()
        self.assertEqual(self.ns['MDDialog'].call_count, 2)
        self.assertEqual(self.ns['Clock'].schedule_once.call_count, 2)

    def test_no_update_consumes_result(self):
        request_id = self.ui._update_request_id
        self.ui._handle_update_result('0.4.1', '0.4.1', request_id)
        self.ui._handle_update_result('0.4.1', '0.4.2', request_id)
        self.ns['MDDialog'].assert_not_called()
        self.ns['Clock'].schedule_once.assert_called_once()

    def test_old_scheduled_redirect_and_button_are_ignored(self):
        self.ui._handle_update_result('0.4.1', '0.4.2', self.ui._update_request_id)
        old_button = self.ns['MDFlatButton'].call_args_list[0].kwargs['on_release']
        self.ui._redirect_to_overview()
        old_redirect = self.ns['Clock'].schedule_once.call_args.args[0]
        self.ui.check_for_updates()
        old_redirect(0)
        self.ns['MDApp'].get_running_app.assert_not_called()
        with patch('webbrowser.open') as browser:
            old_button(None)
            browser.assert_not_called()
        self.assertFalse(self.ui._update_redirect_scheduled)

    def test_thread_delivers_its_captured_request_id(self):
        first_worker = self.ns['Thread'].call_args.kwargs['target']
        self.ui.check_for_updates()
        second_worker = self.ns['Thread'].call_args.kwargs['target']
        self.ns['api_lastestVersion'] = Mock(return_value='0.4.2')
        first_worker()
        old_result = self.ns['Clock'].schedule_once.call_args.args[0]
        old_result(0)
        self.ns['MDDialog'].assert_not_called()
        second_worker()
        new_result = self.ns['Clock'].schedule_once.call_args.args[0]
        new_result(0)
        new_result(0)
        self.ns['MDDialog'].assert_called_once()

    def test_old_thread_error_is_ignored(self):
        old_worker = self.ns['Thread'].call_args.kwargs['target']
        self.ui.check_for_updates()
        self.ns['api_lastestVersion'] = Mock(side_effect=RuntimeError())
        old_worker()
        callback = self.ns['Clock'].schedule_once.call_args.args[0]
        self.ns['Clock'].schedule_once.reset_mock()
        callback(0)
        self.ns['Clock'].schedule_once.assert_not_called()
        self.assertFalse(self.ui._update_result_handled)

    def test_dismiss_and_later_redirect_once(self):
        dialog = Mock()
        self.ui.dialog = dialog
        dialog.dismiss.side_effect = lambda: self.ui._on_dialog_dismiss(dialog)
        self.ui._redirect_to_overview()
        self.ui._redirect_to_overview()
        self.ns['Clock'].schedule_once.assert_called_once()
        self.assertEqual([c[0] for c in dialog.method_calls], ['unbind', 'dismiss'])
        self.setUp()
        self.ui.dialog = dialog
        self.ui._on_dialog_dismiss(dialog)
        self.ui._on_dialog_dismiss(dialog)
        self.ns['Clock'].schedule_once.assert_called_once()

    def test_store_fallback(self):
        for first in [False, RuntimeError()]:
            with self.subTest(first=first):
                self.setUp()
                self.ns.update(platform='ios', APP_STORE_ID='123456')
                with patch('webbrowser.open', side_effect=[first, True]) as browser:
                    self.ui.open_store(None)
                    self.assertEqual(browser.call_count, 2)
                    self.assertTrue(browser.call_args.args[0].startswith('https://apps.apple.com/'))
                self.ns['Clock'].schedule_once.assert_called_once()

    def test_store_absent_or_all_fail(self):
        self.ns['platform'] = 'ios'
        with patch('webbrowser.open') as browser:
            self.ui.open_store(None)
            browser.assert_not_called()
        self.ns['Clock'].schedule_once.assert_called_once()
        self.setUp()
        with patch('webbrowser.open', side_effect=RuntimeError()):
            self.ui.open_store(None)
        self.ns['Clock'].schedule_once.assert_called_once()


if __name__ == '__main__':
    unittest.main()
