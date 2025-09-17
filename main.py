# main.py
# OceanStream – Kivy/KivyMD (iOS + desktop)
# Requer: kivy 2.3.x, KivyMD 1.2.x, kivy-ios, kivy-garden.graph (no iOS)

VERSAO_ATUAL = '0.3.2'

from kivy.resources import resource_add_path, resource_find
import glob

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')

from kivy.utils import platform
IS_IOS = (platform == "ios")
IS_ANDROID = (platform == "android")

from kivy.properties import NumericProperty
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.logger import Logger
from kivy.app import App

from kivymd.uix.dialog import MDDialog
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.card import MDCard
# from kivymd.uix.button import MDRectangleFlatButton, MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.pickers import MDDatePicker
# from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.label import MDLabel
# from kivymd.uix.list import OneLineListItem

from plyer import storagepath

import os, json, requests, jwt, ssl
# from datetime import datetime, timedelta
from datetime import datetime
from threading import Thread

# --- SSL relax (se seu backend exigir) ---
ssl._create_default_https_context = ssl._create_unverified_context

# --- tentar importar sua barra de navegação; cria stub se ausente ---
try:
    from navigation_bar import NavigationBar
except Exception:
    class NavigationBar(Widget):
        def __init__(self, screen_manager=None, logout_callback=None, **kw):
            super().__init__(**kw)
            self.size_hint = (1, None)
            self.height = dp(1)  # stub invisível
            self.logout_callback = logout_callback

# --- caminhos de recursos (iOS-friendly) ---
try:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    APP_DIR = os.getcwd()

# garanta que o Kivy procura recursos no app, /res e /data
for p in {APP_DIR, os.path.join(APP_DIR, "res"), os.path.join(APP_DIR, "data")}:
    try:
        resource_add_path(p)
    except Exception:
        pass

# =====================================================================
#                   ARQUIVOS / DADOS DO APP (iOS-safe)
# =====================================================================

def app_data_dir():
    """Diretório de dados de usuário do app (escrita permitida no iOS)."""
    try:
        app = App.get_running_app()
        if app and getattr(app, "user_data_dir", None):
            os.makedirs(app.user_data_dir, exist_ok=True)
            return app.user_data_dir
    except Exception:
        pass
    # Fallback
    try:
        d = storagepath.get_home_dir()
        if d:
            os.makedirs(d, exist_ok=True)
            return d
    except Exception:
        pass
    d = os.getcwd()
    os.makedirs(d, exist_ok=True)
    return d

def data_path(filename):
    return os.path.join(app_data_dir(), filename)

def tem_atualizacao(v_atual, v_disponivel):
    if not v_disponivel:
        return False
    v_atual_partes = v_atual.split('.')
    v_disp_partes = v_disponivel.split('.')
    parte=0
    for _ in v_disp_partes:
        if not v_atual_partes[parte] or (int(v_disp_partes[parte]) > int(v_atual_partes[parte])):
            return True
        parte+=1
    return False

# =====================================================================
#                          API / AUTENTICAÇÃO
# =====================================================================

API_PRFX = "https://oceanstream-8b3329b99e40.herokuapp.com/"
JWT_FILE = "oceanstream.jwt"
HTTP_TIMEOUT = 25

def _token_file():
    return data_path(JWT_FILE)

def store_access_token(token: str):
    try:
        with open(_token_file(), "w") as f:
            f.write(token or "")
        Logger.info(f"Auth: token salvo em {_token_file()}")
    except Exception as e:
        Logger.exception(f"Auth: erro ao salvar token: {e}")

def get_access_token() -> str:
    try:
        p = _token_file()
        if os.path.exists(p):
            with open(p, "r") as f:
                return (f.read() or "").strip()
    except Exception as e:
        Logger.exception(f"Auth: erro ao ler token: {e}")
    return ""

def delete_access_token():
    try:
        p = _token_file()
        if os.path.exists(p):
            os.remove(p)
            Logger.info("Auth: token deletado.")
    except Exception as e:
        Logger.exception(f"Auth: erro ao deletar token: {e}")

def is_token_valid(token: str) -> bool:
    try:
        if not token:
            return False
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_ts = decoded.get("exp")
        if exp_ts:
            return datetime.fromtimestamp(exp_ts) > datetime.now()
        return False
    except Exception:
        return False

def _auth_headers():
    tok = get_access_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tok}" if tok else "",
    }

def _handle_response(r: requests.Response, endpoint: str):
    if r.status_code == 401:
        Logger.warning(f"HTTP 401 em {endpoint} – token inválido/expirado.")
        return {"__auth_error__": True, "__status__": 401, "__body__": r.text}
    try:
        r.raise_for_status()
        return r.json()
    except Exception as e:
        Logger.exception(f"HTTP erro em {endpoint}: {e} – body: {r.text[:300]}")
        return {"__error__": f"{type(e).__name__}: {e}", "__status__": r.status_code, "__body__": r.text}

def login(email: str, senha: str):
    url = API_PRFX + "login"
    try:
        r = requests.post(url, json={"email": email, "senha": senha},
                          headers={"Content-Type": "application/json"},
                          timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            tok = data.get("accessToken") or data.get("token") or ""
            if tok:
                store_access_token(tok)
                return True, ""
            return False, "Login OK, mas token não recebido."
        else:
            return False, f"Falha no login: {r.status_code} – {r.text}"
    except requests.exceptions.Timeout:
        return False, "Timeout: servidor não respondeu"
    except requests.exceptions.ConnectionError:
        return False, "Sem conexão com o servidor"
    except Exception as e:
        return False, f"Erro: {e}"

def api_dados(nome_tabela: str, start_date: str, end_date: str):
    url = API_PRFX + "dados"
    payload = {"tabela": nome_tabela, "dt_inicial": start_date, "dt_final": f"{end_date} 23:59:59"}
    try:
        r = requests.post(url, headers=_auth_headers(), json=payload, timeout=HTTP_TIMEOUT)
        return _handle_response(r, "POST /dados")
    except Exception as e:
        Logger.exception(f"API /dados erro: {e}")
        return {"__error__": str(e)}

def api_ultimosDados():
    url = API_PRFX + "ultimosDados"
    try:
        r = requests.get(url, headers=_auth_headers(), timeout=HTTP_TIMEOUT)
        return _handle_response(r, "GET /ultimosDados")
    except Exception as e:
        Logger.exception(f"API /ultimosDados erro: {e}")
        return {"__error__": str(e)}

def api_lastestVersion():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}"
    }
    url = API_PRFX+"lastestVersion/"
    try:
        if platform == 'android' or platform == 'win':
            url+='android'
        elif platform == 'ios':
            url+='ios'
        else: # macOS, Linux (desktop) e outros
            pass
        response = requests.post(url, headers=headers, timeout=HTTP_TIMEOUT)

        if response.status_code != 200:
            raise Exception(f"Erro na requisição: {response.status_code} - {response.text}")

        return response.text

    except Exception as e:
        Logger.exception(f"API /ultimosDados erro: {e}")
        return False

# =====================================================================
#                    MAPAS / TABELAS / ARQUIVOS DE UI
# =====================================================================

UNIDADES_MEDIDA = {
    "Bateria":                 "V",
    "Vel. Corr.":              "kt",
    "Dir. Corr.":              "°",
    "Pitch":                   "°",
    "Roll":                    "°",
    "Altura Onda":             "m",
    "Período Onda":            "s",
    "Altura":                  "m",
    "Período":                 "s",
    "Maré Reduzida":           "m",
    "Vel. Vento":              "kt",
    "Rajada":                  "kt",
    "Dir. Vento":              "°",
    "Chuva":                   "mm",
}

PARAMETROS_IMAGENS = {
    "Bateria":                 "res/bateria.png",
    "Vel. Corr.":              "res/corrente- oceanstream.png",
    "Dir. Corr.":              "res/corrente-seta-direita.png",
    "Pitch":                   "res/Pitch-Roll.png",
    "Roll":                    "res/Pitch-Roll.png",
    "Altura Onda":             "res/Onda com linha- oceanstream.png",
    "Período Onda":            "res/Onda - oceanstream.png",
    "Altura":                  "res/Onda com linha- oceanstream.png",
    "Período":                 "res/Onda - oceanstream.png",
    "Maré Reduzida":           "res/Regua maregrafo com seta - oceanstream.png",
    "Vel. Vento":              "res/Pressao atmosferica - oceanstream.png",
    "Rajada":                  "res/Pressao atmosferica - oceanstream.png",
    "Dir. Vento":              "res/Rosa dos ventos - com direcao de cor diferente-oceanstream.png",
    "Chuva":                   "res/Chuva - oceanstream.png",
}

EQUIPAMENTOS_TABELAS = {
    "Boia 04 - Corrente": "ADCP-Boia04_corrente",
    "Boia 08 - Corrente": "ADCP-Boia08_corrente",
    "Boia 10 - Corrente": "ADCP-Boia10_corrente",
    "Boia 04 - Onda":     "ADCP-Boia04_onda",
    "Boia 08 - Onda":     "ADCP-Boia08_onda",
    "Boia 10 - Onda":     "ADCP-Boia10_onda",
    "Ondógrafo Píer-II":  "Ondografo-PII_tab_parametros",
    "Ondógrafo TGL":      "Ondografo-TGL_tab_parametros",
    "Ondógrafo TPD":      "Ondografo-TPD_tab_parametros",
    "Ondógrafo TPM":      "Ondografo-TPM_tab_parametros",
    "Marégrafo":          "Maregrafo-TU_Maregrafo_Troll",
    "Estação Meteorológica": "TU_Estacao_Meteorologica"
}

CABECALHO_TABELA = {
    '_corrente': [
        ['TmStamp', 'Data Hora'],
        ['PNORS_Pitch', 'Pitch'],
        ['PNORS_Roll', 'Roll'],
        ['vel11', 'Vel. Corr.'],
        ['dir11', 'Direção (°)'],
        ['PNORS_Battery_Voltage', 'Bateria (V)'],
    ],
    '_onda': [
        ['TmStamp', 'Data Hora'],
        ['PNORW_Hm0', 'Altura (m)'],
        ['PNORW_Tp', 'Período (s)'],
        ['PNORW_DirTp', 'Direção (°)'],
    ],
    'Ondografo': [
        ['TmStamp', 'Data Hora'],
        ['hm0_alisado', 'Altura (m)'],
        ['tp_alisado', 'Período (s)'],
    ],
    'Estacao': [
        ['TmStamp', 'Data Hora'],
        ['Velocidade_Vento', 'Vel. Vento'],
        ['Rajada_Vento', 'Rajada'],
        ['Direcao_Vento', 'Dir. Vento (°)'],
        ['Chuva', 'Chuva (mm)'],
    ],
    'Maregrafo': [
        ['TmStamp', 'Data Hora'],
        ['Mare_Reduzida', 'Maré Reduzida (m)'],
    ],
}

# ----------------- JSON configs (cards) no user_data_dir -----------------

CARDS_JSON_NAME = "cards.json"
CARDS_JSON_BUNDLED = "data/cards.json"  # arquivo read-only dentro do app

def load_cards_json():
    """Carrega cards do user_data_dir; se não existir, tenta copiar do pacote."""
    user_cards = data_path(CARDS_JSON_NAME)
    if os.path.exists(user_cards):
        try:
            with open(user_cards, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            Logger.exception(f"Erro lendo {user_cards}: {e}")

    # tenta carregar o default embutido no app
    try:
        with open(CARDS_JSON_BUNDLED, "r", encoding="utf-8") as f:
            data = json.load(f)
        # salva uma cópia no user_data_dir para edição futura
        save_cards_json(data)
        return data
    except Exception as e:
        Logger.exception(f"Erro lendo default {CARDS_JSON_BUNDLED}: {e}")
        # fallback mínimo
        return {"nome": "Overview - Cards", "atualizado_em": str(datetime.now()), "cartoes": []}

def save_cards_json(data):
    try:
        with open(data_path(CARDS_JSON_NAME), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        Logger.exception(f"Erro ao salvar {CARDS_JSON_NAME}: {e}")

# =====================================================================
#                               UI
# =====================================================================

def adiciona_unidade(nome, valor):
    if not nome or not valor: # caso algum parametro não tenha sido passado
        Logger.exception(f"Erro ao adicionar unidade de medida: ambos parametros sao obrigatórios.")
        return None

    for grandeza, unidade in UNIDADES_MEDIDA.items():
        if nome == grandeza:
            valor = f'{valor}{unidade}'
            return valor

    Logger.exception(f"Erro ao adicionar unidade de medida: o nome passado não está registrado como uma das grandezas.")
    return None

class StyledCheckbox(MDCheckbox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inactive_color = (1, 1, 1, 1)
        self.active_color = (0.2, 0.6, 1, 1)
        self.size = (dp(48), dp(48))
        self.line_color_normal = (0.8, 0.8, 0.8, 1)

    def animate_checkbox(self, state):
        anim = Animation(active_color=(0.2, 0.6, 1, 1) if state == "down" else (1, 1, 1, 1), duration=0.2)
        anim.start(self)

class CardOverview(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tamanho = (dp(80), dp(60))

    def add_image_scrollable(self, imagens_dados, target_layout=None):
        altura_total = self.tamanho[1] + dp(60)
        scroll = ScrollView(
            size_hint=(1, None),
            height=altura_total,
            scroll_type=['bars', 'content'],
            bar_width=dp(2),
            do_scroll_x=True,
            do_scroll_y=False,
            pos_hint={"top": 1},
        )
        image_row = BoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            height=altura_total,
            padding=[dp(10), dp(20), dp(40), dp(10)],
            spacing=dp(20),
        )
        image_row.bind(minimum_width=image_row.setter('width'))

        for source, top_text, bottom_text in imagens_dados:
            bottom_text = adiciona_unidade(nome=top_text, valor=str(bottom_text))

            layout = BoxLayout(orientation='vertical', size_hint=(None, 1), width=self.tamanho[0], spacing=0)
            top_label = Label(text=top_text, size_hint=(1, None), height=dp(25), color=(0, 0, 0, 1))
            img = Image(source=source, size_hint=(1, None), height=self.tamanho[1], allow_stretch=True, keep_ratio=True)
            bottom_label = Label(text=bottom_text, size_hint=(1, None), height=dp(20), color=(0, 0, 0, 1))
            layout.add_widget(top_label)
            layout.add_widget(img)
            layout.add_widget(bottom_label)
            image_row.add_widget(layout)

        scroll.add_widget(image_row)
        if target_layout:
            target_layout.add_widget(scroll)
        else:
            self.add_widget(scroll)
            self.height = altura_total + dp(20)

class Overview(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cards = []
        dados_cards = load_cards_json()
        self.card_configs = dados_cards.get('cartoes', [])

        self.dicionario_parametros = {
            'Pitch': 'PNORS_Pitch',
            'Roll': 'PNORS_Roll',
            'Vel. Corr.': 'vel11',
            'Dir. Corr.': 'dir11',
            'Bateria': 'PNORS_Battery_Voltage',
            'Altura Onda': 'PNORW_Hm0',
            'Período Onda': 'PNORW_Tp',
            'Altura': 'hm0_alisado',
            'Período': 'tp_alisado',
            'Maré Reduzida': 'Mare_Reduzida',
            'Vel. Vento': 'Velocidade_Vento',
            'Rajada': 'Rajada_Vento',
            'Dir. Vento': 'Direcao_Vento',
            'Chuva': 'Chuva',
        }

    def on_enter(self):
        self.genereate_cards()

    def on_leave(self):
        # Mantém a flag para não verificar novamente
        pass

    def _show_api_msg(self, text):
        self.ids.card_container.clear_widgets()
        self.ids.card_container.add_widget(MDLabel(text=text, halign="center", theme_text_color="Error"))

    def _clear_api_msg(self):
        self.ids.card_container.clear_widgets()

    def card_maximizado(self, card, config, str_datetime, idx, imagens_dados=None):
        card.clear_widgets()
        layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(10), dp(10), dp(10), dp(10)], size_hint=(1, None))
        layout.bind(minimum_height=layout.setter("height"))
        card.add_widget(layout)
        if imagens_dados:
            card.add_image_scrollable(imagens_dados, target_layout=layout)
        card.height = max(dp(180), layout.height + dp(20))
        return card

    def identifica_e_retorna_dados(self, equipment, ultimosDados):
        if '04' in equipment:
            return [ultimosDados['ADCP-Boia04_corrente'], ultimosDados['ADCP-Boia04_onda']]
        if '08' in equipment:
            return [ultimosDados['ADCP-Boia08_corrente'], ultimosDados['ADCP-Boia08_onda']]
        if '10' in equipment:
            return [ultimosDados['ADCP-Boia10_corrente'], ultimosDados['ADCP-Boia10_onda']]
        if 'II' in equipment:
            return ultimosDados['Ondografo-PII_tab_parametros']
        if 'TGL' in equipment:
            return ultimosDados['Ondografo-TGL_tab_parametros']
        if 'TPD' in equipment:
            return ultimosDados['Ondografo-TPD_tab_parametros']
        if 'TPM' in equipment:
            return ultimosDados['Ondografo-TPM_tab_parametros']
        if 'Est' in equipment:
            return ultimosDados['TU_Estacao_Meteorologica']
        if 'Mar' in equipment:
            return ultimosDados['Maregrafo-TU_Maregrafo_Troll']

    def genereate_cards(self):
        self.ids.card_container.clear_widgets()
        self.ids.card_container.add_widget(MDLabel(text="Carregando dados...", halign="center", theme_text_color="Hint"))
        Thread(target=self._generate_cards_threaded, daemon=True).start()

    def _generate_cards_threaded(self):
        app = MDApp.get_running_app()
        selected_parameters = app.selected_parameters

        ultimosDados = api_ultimosDados()

        # --- tratamento de erro da API ---
        if not ultimosDados:
            Clock.schedule_once(lambda dt: self._show_api_msg("Sem dados recebidos da API."), 0)
            return

        if "__auth_error__" in ultimosDados:
            def _to_login(_dt):
                try:
                    delete_access_token()
                except Exception:
                    pass
                MDApp.get_running_app().gerenciador.current = "login"
            Clock.schedule_once(lambda dt: self._show_api_msg("Sessão expirada. Faça login novamente."), 0)
            Clock.schedule_once(_to_login, 0.1)
            return

        if "__error__" in ultimosDados:
            msg = ultimosDados.get("__error__") or "Erro genérico ao consultar a API."
            Clock.schedule_once(lambda dt: self._show_api_msg(f"Erro ao carregar dados:\n{msg}"), 0)
            return
        # --- fim tratamento de erro ---

        cards_data = []
        for idx, config in enumerate(self.card_configs):
            equipment = config.get("text")
            is_active = equipment in selected_parameters
            if not is_active:
                continue

            dados = self.identifica_e_retorna_dados(equipment=equipment, ultimosDados=ultimosDados)
            if dados is None:
                continue

            if isinstance(dados, list):
                # boia corrente + onda
                data_hora = dados[0].get('TmStamp', '')[:-5]
                awac = True
            else:
                data_hora = dados.get('TmStamp', '')[:-5]
                awac = False

            imagens_dados = []
            for param in selected_parameters[equipment]:
                if param in PARAMETROS_IMAGENS:
                    coluna = self.dicionario_parametros[param]
                    try:
                        if awac:
                            if 'PNORW' in coluna:
                                dado = f"{float(dados[1][coluna]):.2f}"
                            else:
                                dado = f"{float(dados[0][coluna]):.2f}"
                        else:
                            dado = f"{float(dados[coluna]):.2f}"
                    except Exception:
                        dado = "-"
                    imagens_dados.append((PARAMETROS_IMAGENS[param], param, dado))

            cards_data.append({
                'equipment': equipment,
                'data_hora': data_hora,
                'imagens_dados': imagens_dados,
                'config': config,
                'idx': idx
            })

        Clock.schedule_once(lambda dt: self._update_ui(cards_data))

    def _update_ui(self, cards_data):
        self.cards_data = cards_data
        self.cards_index = 0
        self.cards.clear()
        self._clear_api_msg()
        Clock.schedule_once(self._add_next_card)

    def _add_next_card(self, dt=None):
        if self.cards_index < len(self.cards_data):
            card_info = self.cards_data[self.cards_index]

            header_card = MDCard(size_hint=(1, None), height=dp(40),
                                 md_bg_color=(0.9, 0.9, 0.95, 1),
                                 padding=[dp(10), dp(5), dp(10), dp(5)],
                                 radius=[dp(12)] , elevation=1)
            header_label = Label(text=f"{card_info['equipment']} - último dado: {card_info['data_hora']}",
                                 color=(0, 0, 0, 1), halign="left", valign="middle")
            header_card.add_widget(header_label)
            self.ids.card_container.add_widget(header_card)

            new_card = CardOverview()
            self.card_maximizado(new_card, card_info['config'], card_info['data_hora'], card_info['idx'], imagens_dados=card_info['imagens_dados'])
            self.cards.append(new_card)
            self.ids.card_container.add_widget(new_card)

            self.cards_index += 1
            Clock.schedule_once(self._add_next_card, 0.02)
        else:
            self.ids.card_container.add_widget(Widget(size_hint_y=None, height=65))
            save_cards_json({"nome": "Overview - Cards", "atualizado_em": str(datetime.now()), "cartoes": self.card_configs})

class Alertas(MDScreen):
    pass

# =========================== Equipamento (gráfico/tabela + gaveta) ===========================

class Equipamento(MDScreen):
    equip = None
    data = []
    cor_label = (0, 0, 0, 1)
    is_landscape = False
    canvas_widget = None
    TIPOS_EQUIPAMENTO = {'_corrente', '_onda', 'Ondografo', 'Estacao', 'Maregrafo'}

    # estado da gaveta
    _drawer_open = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_resize=self._on_window_resize)
        self.build_ui()

    # ---------- Drawer (menu sanduíche) ----------
    def _on_window_resize(self, *_):
        """Mantém a gaveta colada na borda direita ao girar/alterar tamanho."""
        drawer = self.ids.get('right_drawer')
        if drawer:
            if self._drawer_open:
                drawer.x = self.width - drawer.width
            else:
                drawer.x = self.width
        # também recalcula orientação
        self.detect_orientation(None, *Window.size)

    def open_equipment_drawer(self):
        """Abre a gaveta lateral direita."""
        scrim = self.ids.get('drawer_scrim')
        drawer = self.ids.get('right_drawer')
        if not scrim or not drawer:
            Logger.warning("Equipamento: ids 'drawer_scrim'/'right_drawer' não encontrados.")
            return

        scrim.disabled = False
        Animation(opacity=0.4, d=0.2).start(scrim)

        target_x = self.width - drawer.width
        Animation(x=target_x, d=0.25, t="out_cubic").start(drawer)
        self._drawer_open = True

    def close_equipment_drawer(self):
        """Fecha a gaveta lateral direita."""
        scrim = self.ids.get('drawer_scrim')
        drawer = self.ids.get('right_drawer')
        if not scrim or not drawer:
            Logger.warning("Equipamento: ids 'drawer_scrim'/'right_drawer' não encontrados.")
            return

        def _disable_scrim(*_):
            scrim.disabled = True

        anim_scrim = Animation(opacity=0.0, d=0.2)
        anim_scrim.bind(on_complete=lambda *_: _disable_scrim())
        anim_scrim.start(scrim)

        Animation(x=self.width, d=0.25, t="out_cubic").start(drawer)
        self._drawer_open = False

    def _populate_equipment_drawer(self):
        """Cria a lista de botões de equipamentos dentro da gaveta."""
        cont = self.ids.get('drawer_list')
        if not cont:
            Logger.warning("Equipamento: id 'drawer_list' não encontrado.")
            return

        cont.clear_widgets()
        equipamentos = [
            "Boia 04 - Corrente", "Boia 08 - Corrente", "Boia 10 - Corrente",
            "Boia 04 - Onda", "Boia 08 - Onda", "Boia 10 - Onda",
            "Ondógrafo Píer-II", "Ondógrafo TGL", "Ondógrafo TPD",
            "Ondógrafo TPM", "Marégrafo", "Estação Meteorológica"
        ]

        for nome in equipamentos:
            btn = MDFlatButton(
                text=nome,
                size_hint=(1, None),
                height=dp(44),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                md_bg_color=(0, 0, 0, 0),
                ripple_color=(1, 1, 1, 0.15),
                on_release=lambda inst, x=nome: self._choose_equipment_from_drawer(x)
            )
            cont.add_widget(btn)

    def _choose_equipment_from_drawer(self, text):
        self.close_equipment_drawer()
        Clock.schedule_once(lambda *_: self.set_equipamento(text), 0.05)

    # ---------- Fluxo de seleção / dados ----------
    def equip_selected(self, text):
        if text == "Selecione um equipamento":
            return
        if text in EQUIPAMENTOS_TABELAS:
            self.equip = EQUIPAMENTOS_TABELAS[text]
            self.ids.titulo.text = text

            start_date = self.start_date_btn.text
            end_date = self.end_date_btn.text
            self.req_api(start_date, end_date, self.equip)
            self.update_view()

            if self.is_landscape:
                pass
                #self.plot_graph()

    def set_equipamento(self, text):
        """Chame ao escolher no drawer."""
        self.ids.titulo.text = text
        self.equip_selected(text)

    # ---------- UI / Orientação ----------
    def detect_orientation(self, instance, width, height):
        landscape = width > height
        if landscape != self.is_landscape:
            self.is_landscape = landscape
            self.update_view()

    def toggle_header_visibility(self, visible: bool):
        """Mostra/oculta a barra de filtros (datas) e o cabeçalho da tabela."""
        box_dt = self.ids.get('box_dt')
        header_table = self.ids.get('header_table')

        if box_dt:
            box_dt.height = dp(50) if visible else 0
            box_dt.opacity = 1 if visible else 0
            box_dt.disabled = not visible

        if header_table:
            header_table.height = dp(40) if visible else 0
            header_table.opacity = 1 if visible else 0
            header_table.disabled = not visible

    def update_view(self):
        layout = self.ids.container
        if self.canvas_widget:
            layout.remove_widget(self.canvas_widget)
            self.canvas_widget = None

        # rebuild_table(clear_only=True) quando for esconder tabela no landscape
        self.rebuild_table(clear_only=self.is_landscape)
        if self.is_landscape:
            self.toggle_header_visibility(False)
            if self.data:
                pass
                #self.plot_graph()
        else:
            self.toggle_header_visibility(True)
            self.rebuild_table()

    def rebuild_table(self, clear_only=False):
        table_h = self.ids.header_table
        table = self.ids.data_table
        table.clear_widgets()
        table_h.clear_widgets()
        if clear_only:
            return
        self.build_ui()
        self.update_table()

    def build_ui(self):
        layout = self.ids.box_dt
        layout.clear_widgets()

        hoje = datetime.now().strftime("%Y-%m-%d")
        self.start_date_btn = MDRaisedButton(text=hoje, on_release=self.show_start_date_picker)
        self.end_date_btn = MDRaisedButton(text=hoje, on_release=self.show_end_date_picker)
        generate_button = MDRaisedButton(text="Gerar Dados", on_release=self.validate_dates)

        layout.add_widget(self.start_date_btn)
        layout.add_widget(self.end_date_btn)
        layout.add_widget(generate_button)

    def show_start_date_picker(self, instance):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.set_start_date)
        date_dialog.open()

    def set_start_date(self, instance, value, date_range):
        self.start_date_btn.text = value.strftime("%Y-%m-%d")

    def show_end_date_picker(self, instance):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.set_end_date)
        date_dialog.open()

    def set_end_date(self, instance, value, date_range):
        self.end_date_btn.text = value.strftime("%Y-%m-%d")

    # ---------- API / Tabela ----------
    def req_api(self, start_date, end_date, equip=None):
        self.data = []
        equipamento = equip if equip else self.equip
        dados = api_dados(equipamento, start_date, end_date)

        if not dados:
            return
        if "__auth_error__" in dados:
            delete_access_token()
            MDApp.get_running_app().gerenciador.current = "login"
            return
        if "__error__" in dados:
            Logger.error(f"Equipamento: erro API {dados['__error__']}")
            return

        for e in self.TIPOS_EQUIPAMENTO:
            if e in equipamento:
                colunas = CABECALHO_TABELA[e]
                for d in dados:
                    self.data.append([d.get(c[0], "") for c in colunas])

        self.data.reverse()
        self.update_table()

    def update_table(self):
        table_h = self.ids.header_table
        table = self.ids.data_table
        table_h.clear_widgets()
        table.clear_widgets()

        tam_col_1 = dp(120)

        for e in self.TIPOS_EQUIPAMENTO:
            if self.equip and e in self.equip:
                colunas = CABECALHO_TABELA[e]
                table.cols = len(colunas)
                table_h.cols = len(colunas)
                table_h.cols_minimum = {0: tam_col_1}
                table.cols_minimum = {0: tam_col_1}

                for i, coluna in enumerate(colunas):
                    # Use markup para "negrito" em Label padrão
                    lbl = Label(text=f"[b]{coluna[1]}[/b]", markup=True, color=self.cor_label, font_size=dp(10.5))
                    if i == 0:
                        lbl.text_size = (tam_col_1, None)
                    table_h.add_widget(lbl)

        def format_cell_value(value):
            if value is None or value == "":
                return "-"
            return str(value)

        for row in self.data:
            for i, cell in enumerate(row):
                lbl = Label(text=format_cell_value(cell), color=self.cor_label, font_size=dp(16))
                if i == 0:
                    lbl.text_size = (tam_col_1, None)
                table.add_widget(lbl)

    def validate_dates(self, instance):
        start_date = self.start_date_btn.text
        end_date = self.end_date_btn.text
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if (end - start).days > 7:
                self.end_date_btn.text = "Erro: Máx. 7 dias"
            else:
                self.req_api(start_date, end_date)
        except ValueError:
            self.start_date_btn.text = "YYYY-MM-DD"
            self.end_date_btn.text = "YYYY-MM-DD"

    # ---------- Gráfico ----------
    def plot_graph(self):
        pass

    # ---------- KV lifecycle ----------
    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        # prepara gaveta
        self._populate_equipment_drawer()
        drawer = self.ids.get('right_drawer')
        scrim = self.ids.get('drawer_scrim')
        if drawer:
            drawer.x = self.width  # começa fora da tela
        if scrim:
            scrim.opacity = 0
            scrim.disabled = True

# ============================== Login Screen ==============================

class TelaLogin(MDScreen):
    email = None
    senha = None
    _kb_bound = False
    _last_focus_widget = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._kb_bound = False
        self._last_focus_widget = None
        self._pending_redirect = False  # Controla se há um redirecionamento pendente

    def on_kv_post(self, base_widget):
        Clock.schedule_once(self.verifica_token, 1.90)
        super().on_kv_post(base_widget)
        if "root_box" in self.ids:
            self.ids.root_box.y = 0

        if IS_IOS and not getattr(self, "_kb_bound", False):
            Window.bind(on_keyboard_height=self._on_keyboard_height)
            self._kb_bound = True

        # bind foco uma vez
        for name in ("email", "senha"):
            w = self.ids.get(name)
            if w and not getattr(w, "_focus_bound", False):
                w.bind(focus=self.on_field_focus)
                w._focus_bound = True

    def on_pre_enter(self):
        if "root_box" in self.ids:
            self.ids.root_box.y = 0

    def on_pre_leave(self):
        if getattr(self, "_kb_bound", False):
            try:
                Window.unbind(on_keyboard_height=self._on_keyboard_height)
            except Exception:
                pass
            self._kb_bound = False
        if "root_box" in self.ids:
            self.ids.root_box.y = 0

    def on_field_focus(self, widget, focus):
        if IS_IOS:
            if focus:
                self._last_focus_widget = widget
            else:
                kb = self._keyboard_pixels(Window, getattr(Window, "keyboard_height", 0))
                if kb <= 0 and "root_box" in self.ids:
                    Animation.cancel_all(self.ids.root_box, "y")
                    self.ids.root_box.y = 0

    def _keyboard_pixels(self, win, height):
        try:
            h = float(height or 0)
        except Exception:
            h = 0
        if 0 < h <= 1:
            h *= win.height
        return max(0, h)

    def _widget_bottom_to_window(self, widget):
        if not widget:
            return None
        try:
            _, yw = widget.to_window(widget.x, widget.y)
            return yw
        except Exception:
            return None

    def _on_keyboard_height(self, win, height):
        if "root_box" not in self.ids:
            return

        kb_px = self._keyboard_pixels(win, height)
        if kb_px <= 0:
            Animation.cancel_all(self.ids.root_box, "y")
            Animation(y=0, d=0.12, t="out_quad").start(self.ids.root_box)
            return

        ref = self._last_focus_widget or self.ids.get("email") or self.ids.get("card_login")
        bottom = self._widget_bottom_to_window(ref)
        if bottom is None:
            return

        safety = dp(12)
        visible_floor = kb_px + safety

        if bottom < visible_floor:
            delta = visible_floor - bottom
            target = max(0, delta)
        else:
            target = 0

        cur = self.ids.root_box.y
        if abs(cur - target) > 1:
            Animation.cancel_all(self.ids.root_box, "y")
            Animation(y=target, d=0.12, t="out_quad").start(self.ids.root_box)

    def submit(self):
        email = self.ids.get("email").text if self.ids.get("email") else ""
        senha = self.ids.get("senha").text if self.ids.get("senha") else ""
        ok, msg = login(email, senha)
        if ok:
            self.check_for_updates()
        else:
            lbl = self.ids.get("error_message")
            if lbl:
                lbl.text = msg or "Falha no login."
                lbl.opacity = 0
                Animation(opacity=1, d=0.3).start(lbl)
        if self.ids.get("senha"):
            self.ids.senha.text = ""

    def verifica_token(self, *args):
        app = MDApp.get_running_app()
        token = get_access_token()
        if is_token_valid(token):
            # Verifica atualização antes de redirecionar
            self.check_for_updates()
        else:
            delete_access_token()
            app.gerenciador.current = "login"

    def check_for_updates(self):
        """Verifica se há atualizações disponíveis antes de redirecionar para o overview"""
        current_version = VERSAO_ATUAL
        latest_version = api_lastestVersion()

        if latest_version and tem_atualizacao(current_version, latest_version):
            self.show_update_dialog(current_version, latest_version)
        else:
            # Não há atualização, pode redirecionar diretamente
            self._redirect_to_overview()

    def show_update_dialog(self, current_version, latest_version):
        """Mostra diálogo de atualização disponível"""
        texto = f"Atualização disponível!\n\nVersão atual: {current_version}\nVersão disponível: {latest_version}"
        self.dialog = MDDialog(
            title="Atualização Disponível",
            text=texto,
            buttons=[
                MDFlatButton(
                    text="Atualizar",
                    on_release=self.open_store
                ),
                MDFlatButton(
                    text="Mais tarde",
                    on_release=self._redirect_to_overview
                ),
            ],
        )
        self.dialog.open()

    def open_store(self, instance):
        """Abre a loja de aplicativos"""
        try:
            store_urls = {
                'android': "https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream",
                'ios': "[iOS_direct_link]",
                'win': "https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream",
                'windows': "https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream"
            }
            
            import webbrowser
            url = store_urls.get(platform, store_urls['android'])
            webbrowser.open(url)
            
        except Exception as e:
            print(f"Erro ao abrir loja: {e}")
            import webbrowser
            webbrowser.open("https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream")
        
        finally:
            # Redireciona mesmo após tentar abrir a loja
            self._redirect_to_overview()

    def _redirect_to_overview(self, instance=None):
        self.dialog.dismiss()
        """Redireciona para a tela overview"""
        app = MDApp.get_running_app()
        app.gerenciador.current = 'overview'

# ============================ Configuração UI ============================

class Configuracao(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first = True
        self.dicionario_parametros = {
            'Pitch': 'pitch', 'Roll': 'roll',
            'Vel. Corr.': 'vel', 'Dir. Corr.': 'dir',
            'Altura Onda': 'altura', 'Período Onda': 'periodo',
            'Altura': 'altura', 'Período': 'periodo',
            'Bateria': 'bateria', 'Maré Reduzida': 'mare',
            'Vel. Vento': 'velvento', 'Rajada': 'rajada',
            'Dir. Vento': 'dirvento', 'Chuva': 'chuva',
        }

    def on_enter(self):
        if self.first:
            self.seleciona_chkbx()
            self.first = False

    def identifica_equipamento(self, equip):
        id_base = 'chkbx_'
        if 'Boia' in equip:
            if '04' in equip: return id_base + 'b04_'
            if '08' in equip: return id_base + 'b08_'
            if '10' in equip: return id_base + 'b10_'
        elif 'Marégraf' in equip:
            return id_base + 'maregrafo_'
        elif 'Estação' in equip:
            return id_base + 'estacao_'
        elif 'Ondógrafo' in equip:
            if 'II' in equip:  return id_base + 'pii_'
            if 'TGL' in equip: return id_base + 'tgl_'
            if 'TPD' in equip: return id_base + 'tpd_'
            if 'TPM' in equip: return id_base + 'tpm_'
        return id_base

    def seleciona_chkbx(self):
        app = MDApp.get_running_app()
        overview_screen = app.gerenciador.get_screen('overview')
        for card_config in overview_screen.card_configs:
            if not card_config.get('selecionado'):
                continue
            equip = card_config['text']
            id_equip = self.identifica_equipamento(equip)
            for parametro in card_config['selecionado']:
                id_parametro = self.dicionario_parametros.get(parametro)
                if not id_parametro:
                    continue
                chkbx_id = f'{id_equip}{id_parametro}'
                self.alterar_estado_checkbox(chkbx_id, 'down')

    def alterar_estado_checkbox(self, checkbox_id, novo_estado):
        if checkbox_id in self.ids:
            checkbox = self.ids[checkbox_id]
            if isinstance(checkbox, StyledCheckbox):
                checkbox.state = novo_estado

# ============================ Splash / Manager ===========================

class SplashScreen(MDScreen):
    def on_kv_post(self, base_widget):
        Clock.schedule_once(self.start_animation, 0.5)

    def start_animation(self, *args):
        logo = self.ids.logo
        title = self.ids.title
        anim_logo = Animation(opacity=1, y=logo.y + 30, duration=2.4, t="out_quad")
        anim_title = Animation(opacity=1, y=title.y + 30, duration=2.4, t="out_quad")
        anim_logo.start(logo)
        anim_title.start(title)
        Clock.schedule_once(self.verifica_token, 5.5)

    def verifica_token(self, *args):
        app = MDApp.get_running_app()
        token = get_access_token()
        if is_token_valid(token):
            app.gerenciador.current = "overview"
        else:
            delete_access_token()
            app.gerenciador.current = "login"

class GerenciadorTelas(MDScreenManager):
    pass

# ================================ APP ==================================

class OceanStream(MDApp):
    # Expostos ao KV para lidar com o notch / safe area
    safe_top = NumericProperty(0)
    safe_bottom = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_parameters = {}

        # Carrega seleção inicial dos cards
        dados_cards = load_cards_json() or {}
        for equip in (dados_cards.get('cartoes') or []):
            if equip.get('selecionado'):
                self.selected_parameters[equip['text']] = equip['selecionado'][:]

        self.root_layout = None
        self.gerenciador = None
        self.navigation_bar = None

    def build(self):
        # Comportamento do teclado
        if IS_IOS:
            # mantém a tela fixa quando o teclado sobe
            Window.softinput_mode = ''   # valores válidos: '', 'below_target', 'pan', 'scale', 'resize'
        elif IS_ANDROID:
            Window.softinput_mode = 'resize'
        else:
            Window.size = (dp(360), dp(640))

        # Carrega os arquivos KV
        Builder.load_file('paginas/splash.kv')
        Builder.load_file('paginas/overview.kv')
        Builder.load_file('paginas/alertas.kv')
        Builder.load_file('paginas/login.kv')
        Builder.load_file('paginas/configuracao.kv')
        Builder.load_file('paginas/equipamento.kv')

        # Monta a hierarquia de telas
        self.root_layout = FloatLayout()
        self.gerenciador = GerenciadorTelas()

        #self.gerenciador.add_widget(SplashScreen(name='splash'))
        self.gerenciador.add_widget(Overview(name='overview'))
        self.gerenciador.add_widget(Alertas(name='alertas'))
        self.gerenciador.add_widget(TelaLogin(name='login'))
        self.gerenciador.add_widget(Configuracao(name='configuracao'))
        self.gerenciador.add_widget(Equipamento(name='equipamento'))

        self.gerenciador.bind(current=self.on_screen_change)
        self.gerenciador.size_hint = (1, 1)
        self.root_layout.add_widget(self.gerenciador)

        # Inicial
        self.gerenciador.current = 'login'
        return self.root_layout

    def on_start(self):
        # Calcula a safe area no início e mantém atualizada em mudanças de tamanho/orientação
        self._update_safe_area()
        Window.bind(on_resize=lambda *_: self._update_safe_area())

    # ---------- Safe Area helpers ----------
    def _has_notch_like_ratio(self):
        # Heurística: iPhones com notch têm razão de aspecto > ~1.8
        w, h = Window.size
        if not w or not h:
            return True
        ratio = max(w, h) / float(min(w, h))
        return ratio > 1.8

    def _update_safe_area(self):
        if platform == 'ios':
            portrait = Window.height >= Window.width
            if portrait:
                if self._has_notch_like_ratio():
                    self.safe_top = dp(44)     # status bar + notch
                    self.safe_bottom = dp(34)  # home indicator
                else:
                    self.safe_top = dp(20)     # iPhones sem notch
                    self.safe_bottom = 0
            else:
                # Em landscape, top geralmente 0; reserve um pouco no bottom se tiver notch
                self.safe_top = 0
                self.safe_bottom = dp(21) if self._has_notch_like_ratio() else 0
        else:
            self.safe_top = 0
            self.safe_bottom = 0
    # --------------------------------------

    def on_screen_change(self, instance, screen_name):
        if screen_name == 'overview':
            if not self.navigation_bar:
                self.navigation_bar = NavigationBar(
                    screen_manager=self.gerenciador,
                    logout_callback=self.logout
                )
                # evita duplicar caso já esteja num parent
                if self.navigation_bar.parent:
                    self.root_layout.remove_widget(self.navigation_bar)

                self.navigation_bar.size_hint = (1, None)
                self.navigation_bar.height = dp(56)
                self.navigation_bar.pos_hint = {"x": 0, "y": 0}
                self.root_layout.add_widget(self.navigation_bar)
        else:
            if self.navigation_bar:
                # remove a barra quando sai do overview
                self.root_layout.clear_widgets()
                self.root_layout.add_widget(self.gerenciador)
                self.navigation_bar = None

    def toggle_parameter(self, equipment, parameter, state):
        # Atualiza estrutura em memória
        if equipment not in self.selected_parameters:
            self.selected_parameters[equipment] = []

        if state == 'down':
            if parameter not in self.selected_parameters[equipment]:
                self.selected_parameters[equipment].append(parameter)
        else:
            if parameter in self.selected_parameters[equipment]:
                self.selected_parameters[equipment].remove(parameter)

        # Atualiza a configuração persistida (cards.json)
        overview_screen = self.gerenciador.get_screen('overview')
        for card in overview_screen.card_configs:
            if card['text'] == equipment:
                if state == 'down':
                    if parameter not in card['selecionado']:
                        card['selecionado'].append(parameter)
                else:
                    if parameter in card['selecionado']:
                        card['selecionado'].remove(parameter)
                break

        save_cards_json({
            "nome": "Overview - Cards",
            "atualizado_em": str(datetime.now()),
            "cartoes": overview_screen.card_configs
        })

        # Se já está no overview, re-renderiza os cards
        if self.gerenciador.current == "overview":
            self.gerenciador.get_screen("overview").genereate_cards()

    def logout(self):
        delete_access_token()
        self.gerenciador.current = 'login'

if __name__ == '__main__':
    OceanStream().run()
