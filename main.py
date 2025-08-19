from kivymd.app import MDApp
from kivymd.uix.button import MDRectangleFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy_garden.matplotlib import FigureCanvasKivyAgg
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from plyer import storagepath
from datetime import datetime, timedelta
import json
import requests
import os
import jwt
from threading import Thread
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # Backend não interativo (sem UI)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


class StyledCheckbox(MDCheckbox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inactive_color = (1, 1, 1, 1)  # Fundo branco quando desmarcado
        self.active_color = (0.2, 0.6, 1, 1)
        self.size = (dp(48), dp(48))
        self.line_color_normal = (0.8, 0.8, 0.8, 1)  # Borda cinza claro antes de ser selecionado

    def animate_checkbox(self, state):
        if state == "down":
            anim = Animation(active_color=(0.2, 0.6, 1, 1), duration=0.2)  # Azul vibrante quando marcado
        else:
            anim = Animation(active_color=(1, 1, 1, 1), duration=0.2)  # Mantém fundo branco quando desmarcado
        anim.start(self)

Config.set('graphics', 'multisamples', '0')

from navigation_bar import NavigationBar  # Importando a barra de navegação


# Mapeamento de parâmetros para imagens
PARAMETROS_IMAGENS = {
    "Bateria":                 "res/bateria.png",                                                     # Corrente
    "Vel. Corr.":              "res/corrente- oceanstream.png",                                       # Corrente
    "Dir. Corr.":              "res/corrente-seta-direita.png",                                       # Corrente
    "Pitch":                   "res/Pitch-Roll.png",                                                  # Corrente
    "Roll":                    "res/Pitch-Roll.png",                                                  # Corrente
    "Altura Onda":             "res/Onda com linha- oceanstream.png",                                 # Onda
    "Período Onda":            "res/Onda - oceanstream.png",                                          # Onda
    "Altura":                  "res/Onda com linha- oceanstream.png",                                 # Ondógrafo
    "Período":                 "res/Onda - oceanstream.png",                                          # Ondógrafo
    "Maré Reduzida":           "res/Regua maregrafo com seta - oceanstream (2).png",                  # Marégrafo
    "Vel. Vento":              "res/Pressao atmosferica - oceanstream.png",                           # Est.M
    "Rajada":                  "res/Pressao atmosferica - oceanstream.png",                           # Est.M
    "Dir. Vento":              "res/Rosa dos ventos - com direcao de cor diferente-oceanstream.png",  # Est.M
    "Chuva":                   "res/Chuva - oceanstream.png",                                         # Est.M
}
# Mapeamento dos equipamentos para os nomes das tabelas
EQUIPAMENTOS_TABELAS = {
    "Boia 04 - Corrente": "ADCP-Boia04_corrente",
    "Boia 08 - Corrente": "ADCP-Boia08_corrente",
    "Boia 10 - Corrente": "ADCP-Boia10_corrente",
    "Boia 04 - Onda": "ADCP-Boia04_onda",
    "Boia 08 - Onda": "ADCP-Boia08_onda",
    "Boia 10 - Onda": "ADCP-Boia10_onda",
    "Ondógrafo Píer-II": "Ondografo-PII_tab_parametros",
    "Ondógrafo TGL": "Ondografo-TGL_tab_parametros",
    "Ondógrafo TPD": "Ondografo-TPD_tab_parametros",
    "Ondógrafo TPM": "Ondografo-TPM_tab_parametros",
    "Marégrafo": "Maregrafo-TU_Maregrafo_Troll",
    "Estação Meteorológica": "TU_Estacao_Meteorologica"
}
# Cabecalho da tabela na tela Equipamento
CABECALHO_TABELA = {
    '_corrente': [
        ['TmStamp', 'Data Hora']
        ,['PNORS_Pitch', 'Pitch']
        ,['PNORS_Roll', 'Roll']
        ,['vel11', 'Vel. Corr.']
        ,['dir11', 'Direção (°)']
        ,['PNORS_Battery_Voltage', 'Bateria (V)']
    ],
    '_onda': [
        ['TmStamp', 'Data Hora']
        ,['PNORW_Hm0', 'Altura (m)']
        ,['PNORW_Tp', 'Período (s)']
        ,['PNORW_DirTp', 'Direção (°)']
    ],
    'Ondografo': [
        ['TmStamp', 'Data Hora']
        ,['hm0_alisado', 'Altura (m)']
        ,['tp_alisado', 'Período (s)']
    ],
    'Estacao': [
        ['TmStamp', 'Data Hora']
        ,['Velocidade_Vento', 'Vel. Vento']
        ,['Rajada_Vento', 'Rajada']
        ,['Direcao_Vento', 'Dir. Vento (°)']
        ,['Chuva', 'Chuva (mm)']
    ],
    'Maregrafo': [
        ['TmStamp', 'Data Hora']
        ,['Mare_Reduzida', 'Maré Reduzida (m)']
    ]
}
### JWT
JWT_FILE = "oceanstream.jwt"

def get_storage_path():
    if platform == 'android':
        from android.storage import app_storage_path
        return app_storage_path()
    else:
        return storagepath.get_home_dir()

def store_access_token(token):
    app_storage_dir = get_storage_path()
    token_file_path = os.path.join(app_storage_dir, JWT_FILE)
    try:
        with open(token_file_path, 'w') as token_file:
            token_file.write(token)
        Logger.info(f"Token salvo em {token_file_path}")
    except Exception as e:
        Logger.error(f"Erro ao salvar token: {str(e)}")

def get_access_token():
    app_storage_dir = get_storage_path()
    token_file_path = os.path.join(app_storage_dir, JWT_FILE)
    if os.path.exists(token_file_path):
        try:
            with open(token_file_path, 'r') as token_file:
                token = token_file.read()
                Logger.info("JWT recuperado.")
                return token
        except Exception as e:
            Logger.error(f"Erro ao ler token: {str(e)}")
            return ""
    else:
        Logger.info("Nenhum token encontrado.")
        return ""

def delete_access_token():
    app_storage_dir = storagepath.get_home_dir()
    token_file_path = os.path.join(app_storage_dir, JWT_FILE)
    if os.path.exists(token_file_path):
        os.remove(token_file_path)
        print("Token deletado.")
    else:
        print("Nenhum token para deletar.")

def is_token_valid(token):
    try:
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded_token.get('exp')
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            if exp_date > datetime.now():
                return True
        return False
    except Exception as e:
        print(f"Erro ao verificar token: {str(e)}")
        return False

### JSON

def ler_arquivo_json(caminho_arquivo):
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        print("JSON carregado com sucesso!")
        return dados
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar o JSON: {e}")
    return None

def salvar_arquivo_json(data, caminho_arquivo):
    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar JSON: {e}")

def salvar_cards(dict):
    dict_completo = {
        "nome": "Overview - Cards",
        "atualizado_em": str(datetime.now()),
        "cartoes": dict
    }
    salvar_arquivo_json(data=dict_completo, caminho_arquivo='data/cards.json')

dados_cards = ler_arquivo_json(caminho_arquivo='data/cards.json')

### API
API_PRFX = "https://oceanstream-8b3329b99e40.herokuapp.com/"

def verifica_formato_data(data):
    """Verifica se a data está no formato YYYY-MM-DD."""
    try:
        datetime.strptime(data, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# POST /dados
def api_dados(nome_tabela, start_date, end_date):
    # Verifica o formato das datas
    if not (verifica_formato_data(start_date) and verifica_formato_data(end_date)):
        return

    # Adiciona o horário ao final da data final
    end_date = f"{end_date} 23:59:59"

    # Corpo da requisição
    corpo = {
        "tabela": nome_tabela,
        "dt_inicial": start_date,
        "dt_final": end_date
    }

    # Cabeçalhos da requisição
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}"
    }

    # URL da API
    url = API_PRFX+"dados"

    # Faz a requisição POST
    try:
        response = requests.post(url, headers=headers, json=corpo)

        # Verifica se a requisição foi bem-sucedida
        if response.status_code != 200:
            raise Exception(f"Erro na requisição: {response.status_code} - {response.text}")

        # Converte a resposta para JSON
        data = response.json()

        return data

    except Exception as error:
        print(f"Erro: {error}")

# GET /ultimosDados
def api_ultimosDados():
    # Cabeçalhos da requisição
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}"
    }

    # URL da API
    url = API_PRFX+"ultimosDados"

    # Faz a requisição POST
    try:
        response = requests.get(url, headers=headers)

        # Verifica se a requisição foi bem-sucedida
        if response.status_code != 200:
            raise Exception(f"Erro na requisição: {response.status_code} - {response.text}")

        # Converte a resposta para JSON
        data = response.json()

        return data

    except Exception as error:
        print(f"Erro: {error}")

# POST /login
def login(email, senha):
    url = API_PRFX+'login'
    headers = {'Content-Type': 'application/json'}
    corpo = {"email": email, "senha": senha}
    try:
        response = requests.post(url, json=corpo, headers=headers)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('accessToken')
            store_access_token(access_token)
            return [True, '']
        else:
            msg = f"Falha no login: {response.status_code} - {response.text}"
            print(msg)
    except Exception as e:
        msg = f"Erro ao tentar fazer login: {str(e)}"
        print(msg)
    
    return [False, msg]

### Telas

Builder.load_file('paginas/splash.kv')
Builder.load_file('paginas/overview.kv')
Builder.load_file('paginas/alertas.kv')
Builder.load_file('paginas/login.kv')
Builder.load_file('paginas/configuracao.kv')
Builder.load_file('paginas/equipamento.kv')

class CardOverview(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tamanho = (dp(80), dp(60))  # ou (width, height) ideal para suas imagens

    def add_image_scrollable(self, imagens_dados, target_layout=None):
        """Adiciona uma linha horizontal scrollável de imagens com labels dentro de um layout específico (FloatLayout ou direto no Card)."""
        altura_total = self.tamanho[1] + dp(60)

        scroll = ScrollView(
            size_hint=(1, None),
            height=altura_total,
            scroll_type=['bars', 'content'],
            bar_width=dp(2),
            do_scroll_x=True,
            do_scroll_y=False,
            pos_hint={"top": 1}
        )

        image_row = BoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            height=altura_total,
                padding=[dp(10), dp(20), dp(40), dp(10)],  # esquerda, cima, direita, baixo
            spacing=dp(20)
        )
        image_row.bind(minimum_width=image_row.setter('width'))

        for source, top_text, bottom_text in imagens_dados:
            layout = BoxLayout(
                orientation='vertical',
                size_hint=(None, 1),
                width=self.tamanho[0],
                spacing=0
            )

            top_label = Label(
                text=top_text,
                size_hint=(1, None),
                height=dp(25),
                color=(0, 0, 0, 1)
            )

            image = Image(
                source=source,
                size_hint=(1, None),
                height=self.tamanho[1],
                allow_stretch=True,
                keep_ratio=True
            )

            bottom_label = Label(
                text=str(bottom_text),
                size_hint=(1, None),
                height=dp(20),
                color=(0, 0, 0, 1)
            )

            layout.add_widget(top_label)
            layout.add_widget(image)
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
        self.cards = []  # Lista para armazenar os widgets dos cards
        self.card_configs = dados_cards['cartoes']

        self.dicionario_parametros = { # conforme as colunas no banco de dados
                       'Pitch' : 'PNORS_Pitch',
                        'Roll' : 'PNORS_Roll',
                  'Vel. Corr.' : 'vel11',
                  'Dir. Corr.' : 'dir11',
                     'Bateria' : 'PNORS_Battery_Voltage',
                 'Altura Onda' : 'PNORW_Hm0',
                'Período Onda' : 'PNORW_Tp',

                      'Altura' : 'hm0_alisado',
                     'Período' : 'tp_alisado',

               'Maré Reduzida' : 'Mare_Reduzida',

                  'Vel. Vento' : 'Velocidade_Vento',
                      'Rajada' : 'Rajada_Vento',
                  'Dir. Vento' : 'Direcao_Vento',
                       'Chuva' : 'Chuva'
        }

    def card_maximizado(self, card, config, str_datetime, idx, imagens_dados=None):
        card.clear_widgets()

        layout = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=[dp(10), dp(10), dp(10), dp(10)],
            size_hint=(1, None)
        )
        layout.bind(minimum_height=layout.setter("height"))
        card.add_widget(layout)

        if imagens_dados:
            card.add_image_scrollable(imagens_dados, target_layout=layout)

        # card.height = layout.height + 20
        card.height = max(dp(180), layout.height + dp(20))
        return card

    def card_minimizado(self, card, config, str_datetime, idx):
        return self.card_maximizado(card, config, str_datetime, idx)
        # precisa converter para dp
        # falta inserir o datetime aqui no card minimizado
        card.visible = False
        card.clear_widgets()
        card.add_widget(
            Label(
                text=config["text"],
                color=(0.5, 0.5, 0.5, 1),
                height=30, # Define uma altura fixa para o Label
                size_hint_y=None, # Define que a altura não será ajustada automaticamente
                pos_hint={"top": 1}, # Alinha o Label no topo do card
            )
        )
        card.add_widget(
            MDRectangleFlatButton(
                text="Maximizar",
                size_hint=(None, None),
                size=(150, 40),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
                on_release=lambda btn, i=idx: self.toggle_card(i),
            )
        )
        card.height = 60
        return card

    def reorganize_cards(self):
        card_container = self.ids.card_container
        card_container.clear_widgets()
        for card in self.cards:
            card_container.add_widget(card)

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
        # Mostra feedback de carregamento
        self.ids.card_container.clear_widgets()
        self.ids.card_container.add_widget(
            MDLabel(text="Carregando dados...", halign="center", theme_text_color="Hint")
        )
        
        # Inicia o carregamento dos cards em thread separada
        Thread(target=self._generate_cards_threaded, daemon=True).start()


    def _generate_cards_threaded(self):
        app = MDApp.get_running_app()
        selected_parameters = app.selected_parameters
        ultimosDados = api_ultimosDados()
        
        # Prepara os dados que serão usados na UI
        cards_data = []
        for idx, config in enumerate(self.card_configs):
            equipment = config.get("text")
            is_active = equipment in selected_parameters
            if not is_active:
                continue

            dados = self.identifica_e_retorna_dados(equipment=equipment, ultimosDados=ultimosDados)
            if len(dados) == 2:
                data_hora = dados[0]['TmStamp']
                awac = True
            else:
                data_hora = dados['TmStamp']
                awac = False

            data_hora = data_hora[:-5]
            imagens_dados = []
            
            for param in selected_parameters[equipment]:
                if param in PARAMETROS_IMAGENS:
                    coluna = self.dicionario_parametros[param]
                    if awac:
                        if 'PNORW' in coluna:
                            dado = f"{dados[1][coluna]:.2f}"
                        else:
                            dado = f"{dados[0][coluna]:.2f}"
                    else:
                        dado = f"{dados[coluna]:.2f}"
                    imagens_dados.append((PARAMETROS_IMAGENS[param], param, dado))

            cards_data.append({
                'equipment': equipment,
                'data_hora': data_hora,
                'imagens_dados': imagens_dados,
                'config': config,
                'idx': idx
            })

        # Agendando a atualização da UI na thread principal
        Clock.schedule_once(lambda dt: self._update_ui(cards_data))

    def _update_ui(self, cards_data):
        self.cards_data = cards_data      # Armazena os dados para uso em partes
        self.cards_index = 0              # Índice de controle de qual card está sendo adicionado
        self.cards.clear()                # Limpa lista de cards
        self.ids.card_container.clear_widgets()

        # Mostra mensagem de carregamento inicial
        self.ids.card_container.add_widget(
            MDLabel(text="Carregando dados...", halign="center", theme_text_color="Hint")
        )

        # Começa a inserção progressiva
        Clock.schedule_once(self._add_next_card)

    def _add_next_card(self, dt=None):
        if self.cards_index == 0:
            self.ids.card_container.clear_widgets()  # Limpa o "Carregando dados..."

        if self.cards_index < len(self.cards_data):
            card_info = self.cards_data[self.cards_index]

            # Cria o header do card
            header_card = MDCard(
                size_hint=(1, None),
                height=dp(40),
                md_bg_color=(0.9, 0.9, 0.95, 1),
                padding=[dp(10), dp(5), dp(10), dp(5)],
                radius=[dp(12), dp(12), dp(12), dp(12)],
                elevation=1,
            )
            header_label = Label(
                text=f"{card_info['equipment']} - último dado: {card_info['data_hora']}",
                color=(0, 0, 0, 1),
                halign="left",
                valign="middle"
            )
            header_card.add_widget(header_label)
            self.ids.card_container.add_widget(header_card)

            # Cria o card principal
            new_card = CardOverview()
            if card_info['config'].get("maximize", True):
                self.card_maximizado(
                    card=new_card,
                    config=card_info['config'],
                    str_datetime=card_info['data_hora'],
                    idx=card_info['idx'],
                    imagens_dados=card_info['imagens_dados']
                )
            else:
                self.card_minimizado(
                    card=new_card,
                    config=card_info['config'],
                    str_datetime='',
                    idx=card_info['idx']
                )

            self.cards.append(new_card)
            self.ids.card_container.add_widget(new_card)

            self.cards_index += 1
            Clock.schedule_once(self._add_next_card, 0.02)  # 20ms entre cada card
        else:
            # Adiciona espaçamento final
            self.ids.card_container.add_widget(Widget(size_hint_y=None, height=65))
            salvar_cards(self.card_configs)
            print(f'card_config: {self.card_configs}')



    def on_enter(self):
        self.genereate_cards()  

class Alertas(MDScreen):
    pass

class Equipamento(MDScreen):
    equip = None
    data = ListProperty([])
    cor_label = (0, 0, 0, 1)
    is_landscape = False  # Estado atual da orientação
    canvas_widget = None  # Armazena o widget do gráfico para remoção correta

    TIPOS_EQUIPAMENTO = { '_corrente', '_onda', 'Ondografo', 'Estacao', 'Maregrafo' }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_resize=self.detect_orientation)  # Monitora mudanças na tela
        self.build_ui()

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
                self.plot_graph()

    def detect_orientation(self, instance, width, height):
        """Detecta a orientação da tela e atualiza a interface."""
        if platform == 'android':
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            WindowManager = autoclass('android.view.WindowManager')
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            window_manager = context.getSystemService(Context.WINDOW_SERVICE)
            display = window_manager.getDefaultDisplay()
            rotation = display.getRotation()

            # 0 ou 2 é portrait, 1 ou 3 é landscape
            landscape = rotation % 2 == 1
        else:
            landscape = width > height

        if landscape != self.is_landscape:
            self.is_landscape = landscape
            self.update_view()

    def update_view(self):
        """Alterna entre tabela e gráfico dependendo da orientação da tela."""
        layout = self.ids.container

        # Remove todos os widgets do container (gráfico ou tabela)
        if self.canvas_widget:
            layout.remove_widget(self.canvas_widget)
            self.canvas_widget = None

        # Remove a tabela (reconstrói do zero depois, se necessário)
        self.rebuild_table(clear_only=True)

        if self.is_landscape:
            self.toggle_header_visibility(False)  # Esconde cabeçalho e filtros
            if self.data:  # Só plota se já tiver dados
                self.plot_graph()
        else:
            self.toggle_header_visibility(True)   # Mostra tudo
            self.rebuild_table()

    def rebuild_table(self, clear_only=False):
        """Reconstrói a tabela ou apenas limpa, se necessário."""
        table_h = self.ids.header_table
        table = self.ids.data_table

        table.clear_widgets()
        table_h.clear_widgets()

        if clear_only:
            return

        self.build_ui()
        self.update_table()

    def build_ui(self):
        """ Adiciona os elementos da UI para a seleção de datas com calendário """
        layout = self.ids.box_dt
        layout.clear_widgets()  # EVITAR DUPLICAÇÃO

        # Dia de hoje
        hoje = datetime.now()
        hoje_formatado = hoje.strftime("%Y-%m-%d")  # Formato YYYY-MM-DD

        # Dia de ontem
        # ontem = hoje - timedelta(days=1)
        # ontem_formatado = ontem.strftime("%Y-%m-%d")  # Formato YYYY-MM-DD

        # data inicial
        self.start_date_btn = MDRaisedButton(
            text=hoje_formatado,
            on_release=self.show_start_date_picker)
        # data final
        self.end_date_btn = MDRaisedButton(
            text=hoje_formatado,
            on_release=self.show_end_date_picker)
        # botao submit
        generate_button = MDRaisedButton(
            text="Gerar Dados",
            on_release=self.validate_dates)

        layout.add_widget(self.start_date_btn)
        layout.add_widget(self.end_date_btn)
        layout.add_widget(generate_button)

    def show_start_date_picker(self, instance):
        """ Abre o seletor de data para a data de início """
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.set_start_date)
        date_dialog.open()

    def set_start_date(self, instance, value, date_range):
        self.start_date_btn.text = value.strftime("%Y-%m-%d")
    
    def show_end_date_picker(self, instance):
        """ Abre o seletor de data para a data de fim """
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.set_end_date)
        date_dialog.open()

    def set_end_date(self, instance, value, date_range):
        self.end_date_btn.text = value.strftime("%Y-%m-%d")

    def req_api(self, start_date, end_date, equip=None):
        # esvazia lista de dados
        self.data = []
        
        # Usa o equipamento passado como parâmetro ou o atual
        equipamento = equip if equip else self.equip
        
        # Obtém os dados da API
        dados = api_dados(equipamento, start_date, end_date)
        
        # Processa os dados conforme o tipo de equipamento
        for e in self.TIPOS_EQUIPAMENTO:
            if e in equipamento:
                colunas = CABECALHO_TABELA[e]
                for d in dados:
                    self.data.append([ d[c[0]] for c in colunas ])

        self.data.reverse()
        self.update_table()

    def update_table(self):
        """ Atualiza a tabela com os dados """
        table_h = self.ids.header_table
        table = self.ids.data_table

        table_h.clear_widgets()
        table.clear_widgets()

        tam_col_1 = dp(60)

        # Adiciona o cabeçalho
        for e in self.TIPOS_EQUIPAMENTO:
            if e in self.equip:
                colunas = CABECALHO_TABELA[e]
                table.cols = len(colunas)
                table_h.cols = len(colunas)
                
                # Define largura mínima das colunas (primeira coluna maior)
                table_h.cols_minimum = {0: tam_col_1}  # Timestamp mais largo
                table.cols_minimum = {0: tam_col_1}    # Timestamp mais largo
                
                for i, coluna in enumerate(colunas):
                    # Primeira coluna com alinhamento à esquerda e tamanho maior
                    # halign = 'left' if i == 0 else 'center'
                    label = Label(
                        text=coluna[1], 
                        bold=True, 
                        color=self.cor_label,
                        font_size=dp(17),
                        # halign=halign
                    )
                    if i == 0:  # Só para a primeira coluna
                        label.text_size = (tam_col_1, None)  # Largura fixa para a primeira coluna
                        # label.shorten = True  # Encurta texto longo com "..."
                    table_h.add_widget(label)

        # Função para tratar valores inválidos
        def format_cell_value(value):
            if value is None:
                return "-"
            return str(value)

        # Adiciona os dados com tratamento
        for row in self.data:
            for i, cell in enumerate(row):
                # Primeira coluna com alinhamento à esquerda
                # halign = 'left' if i == 0 else 'center'
                label = Label(
                    text=format_cell_value(cell),
                    color=self.cor_label,
                    font_size=dp(16),
                    # halign=halign
                )
                if i == 0:  # Só para a primeira coluna
                    label.text_size = (tam_col_1, None)  # Largura fixa para a primeira coluna
                    # label.shorten = True  # Encurta texto longo com "..."
                table.add_widget(label)
    
    def validate_dates(self, instance):
        """ Valida o intervalo de datas selecionado pelo usuário e atualiza os dados """
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
            self.start_date_btn.text = "Selecionar Data Início"
            self.end_date_btn.text = "Selecionar Data Fim"

    def plot_graph(self):
        """Gera um gráfico com os dados do equipamento selecionado"""
        if not self.data:
            return

        import matplotlib.dates as mdates
        from matplotlib.backend_bases import MouseEvent
        from matplotlib.widgets import Cursor
        from datetime import datetime

        # Limpa o gráfico anterior se existir
        plt.close('all')

        timestamps = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in self.data]

        # Configurações diferentes para cada tipo de equipamento
        if '_corrente' in self.equip:
            # Gráfico para ADCP Corrente
            velocidades = [float(row[1]) for row in self.data]
            direcoes = [float(row[2]) for row in self.data]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            line1, = ax.plot(timestamps, velocidades, marker="o", linestyle="-", color="blue", label="Velocidade (m/s)")
            line2, = ax.plot(timestamps, direcoes, marker="s", linestyle="--", color="red", label="Direção (°)")
            
            ax.set_title("Velocidade e Direção da Corrente")
            ax.set_ylabel("Valor")
            
        elif '_onda' in self.equip:
            # Gráfico para ADCP Onda
            altura = [float(row[1]) for row in self.data]
            periodo = [float(row[2]) for row in self.data]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            line1, = ax.plot(timestamps, altura, marker="o", linestyle="-", color="blue", label="Altura (m)")
            line2, = ax.plot(timestamps, periodo, marker="s", linestyle="--", color="green", label="Período (s)")
            
            ax.set_title("Altura e Período de Onda")
            ax.set_ylabel("Valor")
            
        elif 'Ondografo' in self.equip:
            # Gráfico para Ondógrafo
            altura = [float(row[1]) for row in self.data]
            periodo = [float(row[2]) for row in self.data]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            line1, = ax.plot(timestamps, altura, marker="o", linestyle="-", color="blue", label="Altura (m)")
            line2, = ax.plot(timestamps, periodo, marker="s", linestyle="--", color="green", label="Período (s)")
            
            ax.set_title("Altura e Período de Onda")
            ax.set_ylabel("Valor")
            
        elif 'Estacao' in self.equip:
            # Gráfico para Estação Meteorológica
            vento = [float(row[1]) for row in self.data]
            rajada = [float(row[2]) for row in self.data]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            line1, = ax.plot(timestamps, vento, marker="o", linestyle="-", color="blue", label="Vel. Vento (m/s)")
            line2, = ax.plot(timestamps, rajada, marker="s", linestyle="--", color="red", label="Rajada (m/s)")
            
            ax.set_title("Velocidade do Vento e Rajadas")
            ax.set_ylabel("Velocidade (m/s)")
            
        elif 'Maregrafo' in self.equip:
            # Gráfico para Marégrafo
            mare = [float(row[1]) for row in self.data]
            
            fig, ax = plt.subplots(figsize=(10, 4))
            line1, = ax.plot(timestamps, mare, marker="o", linestyle="-", color="blue", label="Maré Reduzida (m)")
            
            ax.set_title("Nível do Mar")
            ax.set_ylabel("Altura (m)")

        # Configurações comuns a todos os gráficos
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        fig.autofmt_xdate()
        ax.set_xlabel("Tempo")
        ax.legend()
        ax.grid(True)

        # Cursor interativo
        cursor = Cursor(ax, useblit=True, color='black', linewidth=1)

        # Interatividade com texto ao tocar
        annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"), arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)

        def update_annot(ind, line):
            x, y = line.get_data()
            annot.xy = (x[ind[0]], y[ind[0]])
            text = f"{x[ind[0]].strftime('%H:%M')}: {y[ind[0]]:.2f}"
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor('lightyellow')
            annot.get_bbox_patch().set_alpha(0.8)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                for line in [line1, line2] if 'line2' in locals() else [line1]:
                    cont, ind = line.contains(event)
                    if cont:
                        update_annot(ind["ind"], line)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
            if vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)

        if self.canvas_widget:
            self.ids.container.remove_widget(self.canvas_widget)

        self.canvas_widget = FigureCanvasKivyAgg(fig)
        self.canvas_widget.size_hint_y = 1
        self.canvas_widget.pos_hint = {"center_x": 0.5, "center_y": 0.5}

        self.ids.container.add_widget(self.canvas_widget)
   
    def toggle_header_visibility(self, visible):
        header = self.ids.get("titulo", None)
        if header:
            header.opacity = 1 if visible else 0
            header.disabled = not visible

        box_dt = self.ids.box_dt
        header_table = self.ids.header_table

        box_dt.height = dp(50) if visible else 0
        header_table.height = dp(40) if visible else 0

        box_dt.opacity = 1 if visible else 0
        box_dt.disabled = not visible
        header_table.opacity = 1 if visible else 0
        header_table.disabled = not visible

    def build_menu(self):
        equipamentos = [
            "Boia 04 - Corrente", "Boia 08 - Corrente", "Boia 10 - Corrente",
            "Boia 04 - Onda", "Boia 08 - Onda", "Boia 10 - Onda",
            "Ondógrafo Píer-II", "Ondógrafo TGL", "Ondógrafo TPD",
            "Ondógrafo TPM", "Marégrafo", "Estação Meteorológica"
        ]
        self.menu_items = [
            {
                "text": equipamento,
                "height": dp(48),
                "text_color": (0, 0, 0, 1),
                "on_release": lambda x=equipamento: self.set_equipamento(x)
            } for equipamento in equipamentos
        ]

        self.menu = MDDropdownMenu(
            caller=self.ids.titulo_container,
            items=self.menu_items,
            width_mult=4,
            max_height=dp(240),
        )

    def open_equip_menu(self):
        if self.menu:
            self.menu.open()
            self.animate_arrow(up=True)

    def set_equipamento(self, text):
        self.ids.titulo.text = text  # ← Isso troca o texto visualmente
        self.animate_arrow(up=False)  # ← Isso gira a seta de volta para baixo
        self.menu.dismiss()
        self.equip_selected(text)

    def animate_arrow(self, up):
        icon = self.ids.titulo_dropdown_icon
        anim = Animation(rotation=180 if up else 0, duration=0.2)
        anim.start(icon)    

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.build_menu()

class TelaLogin(MDScreen):
    email = ObjectProperty(None)
    senha = ObjectProperty(None)

    def on_enter(self):
        pass

    def submit(self):
        email = self.ids.email.text
        senha = self.ids.senha.text
        
        # Limpa a mensagem de erro anterior
        self.ids.error_message.text = ""
        self.ids.error_message.opacity = 0
        
        try:
            resposta = login(email=email, senha=senha)
            if resposta[0]:
                self.manager.current = 'overview'
            else:
                self.show_error(resposta[1])
        except requests.exceptions.Timeout:
            self.show_error("Timeout: servidor não respondeu")
        except requests.exceptions.ConnectionError:
            self.show_error("Sem conexão com o servidor")
        except Exception as e:
            self.show_error(f"Erro: {str(e)}")
        finally:
            self.ids.senha.text = ""

    def show_error(self, message):
        """Exibe a mensagem de erro com animação"""
        error_label = self.ids.error_message
        error_label.text = message
        self.ids.error_message
        anim = Animation(opacity=1, duration=0.3)
        anim.start(error_label)

class Configuracao(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # apenas no primeiro carregamento precisa consultar os dados do arquivo JSON
        self.first=True

        self.dicionario_parametros = { # conforme os IDs das checkboxes em 'configuracao.kv'
                       'Pitch' : 'pitch',
                        'Roll' : 'roll',
                  'Vel. Corr.' : 'vel',
                  'Dir. Corr.' : 'dir',
                 'Altura Onda' : 'altura',
                'Período Onda' : 'periodo',
                      'Altura' : 'altura',
                     'Período' : 'periodo',
                     'Bateria' : 'bateria',
               'Maré Reduzida' : 'mare',
                  'Vel. Vento' : 'velvento',
                      'Rajada' : 'rajada',
                  'Dir. Vento' : 'dirvento',
                       'Chuva' : 'chuva'
        }

    def on_enter(self):
        if self.first:
            self.seleciona_chkbx()
            self.first=False

    def identifica_equipamento(self, equip):
        id_base = 'chkbx_'
        # adcp
        if 'Boia' in equip:
            if '04' in equip:
                id_equip = id_base+'b04_'
            elif '08' in equip:
                id_equip = id_base+'b08_'
            elif '10' in equip:
                id_equip = id_base+'b10_'
        # maregrafo
        elif 'Marégraf' in equip:
            id_equip = id_base+'maregrafo_'
        # estação
        elif 'Estação' in equip:
            id_equip = id_base+'estacao_'
        # ondografo
        elif 'Ondógrafo' in equip:
            if 'II' in equip:
                id_equip = id_base+'pii_'
            elif 'TGL' in equip:
                id_equip = id_base+'tgl_'
            elif 'TPD' in equip:
                id_equip = id_base+'tpd_'
            elif 'TPM' in equip:
                id_equip = id_base+'tpm_'
        return id_equip

    def seleciona_chkbx(self):
        app = MDApp.get_running_app()
        overview_screen = app.gerenciador.get_screen('overview')
        
        # Percorre cada um dos equipamentos selecionados
        for card_config in overview_screen.card_configs:
            if not card_config['selecionado']:
                continue
                
            equip = card_config['text']
            id_equip = self.identifica_equipamento(equip)

            # Percorre cada um dos parametros do equipamento atual
            for parametro in card_config['selecionado']:
                id_parametro = self.dicionario_parametros[parametro]
                chkbx_id = f'{id_equip}{id_parametro}'
                self.alterar_estado_checkbox(chkbx_id, 'down')

    def alterar_estado_checkbox(self, checkbox_id, novo_estado):
        """
        Altera o estado de uma checkbox específica.
        :param checkbox_id: O ID da checkbox (string).
        :param novo_estado: O novo estado ('down' para marcado, 'normal' para desmarcado).
        """
        if checkbox_id in self.ids:
            checkbox = self.ids[checkbox_id]
            if isinstance(checkbox, StyledCheckbox):
                checkbox.state = novo_estado
            else:
                print(f'O ID {checkbox_id} não é uma StyledCheckbox.')
        else:
            print(f'Checkbox com ID {checkbox_id} não encontrada.')

class SplashScreen(MDScreen):
    def on_kv_post(self, base_widget):
        print(">>> SplashScreen carregada")
        Clock.schedule_once(self.start_animation, 0.5)

    def start_animation(self, *args):
        print(">>> Iniciando animações...")
        logo = self.ids.logo
        title = self.ids.title

        anim_logo = Animation(opacity=1, y=logo.y + 30, duration=2.4, t="out_quad")
        anim_title = Animation(opacity=1, y=title.y + 30, duration=2.4, t="out_quad")

        anim_logo.start(logo)
        anim_title.start(title)

        Clock.schedule_once(self.verifica_token, 5.5)  # <- espera suficiente

    def verifica_token(self, *args):
        print(">>> Verificando token")
        app = MDApp.get_running_app()

        token = get_access_token()
        if is_token_valid(token):
            print(">>> Token válido")
            app.gerenciador.current = "overview"
        else:
            print(">>> Token inválido ou não existe")
            delete_access_token()
            app.gerenciador.current = "login"


class GerenciadorTelas(MDScreenManager):
    pass

class OceanStream(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_parameters = {}

        # Carrega as configurações do JSON
        dados_cards = ler_arquivo_json(caminho_arquivo='data/cards.json')
        if dados_cards:
            for equip in dados_cards['cartoes']:
                if equip['selecionado']:
                    self.selected_parameters[equip['text']] = equip['selecionado'].copy()

    def build(self):
        # Solicitar permissões no Android
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

        from kivy.core.window import Window

        if platform == 'android':
            Window.softinput_mode = 'resize'
        else:
            Window.size = (dp(360), dp(640))


        self.root_layout = FloatLayout()
        self.gerenciador = GerenciadorTelas()

        # Adiciona todas as telas
        self.gerenciador.add_widget(SplashScreen(name='splash'))
        self.gerenciador.add_widget(Overview(name='overview'))
        self.gerenciador.add_widget(Alertas(name='alertas'))
        self.gerenciador.add_widget(TelaLogin(name='login'))
        self.gerenciador.add_widget(Configuracao(name='configuracao'))
        self.gerenciador.add_widget(Equipamento(name='equipamento'))

        self.gerenciador.bind(current=self.on_screen_change)
        self.gerenciador.size_hint = (1, 1)
        self.root_layout.add_widget(self.gerenciador)

        self.navigation_bar = None
        self.gerenciador.current = 'splash'

        return self.root_layout

    def toggle_parameter(self, equipment, parameter, state):
        # Atualiza selected_parameters
        if equipment not in self.selected_parameters:
            self.selected_parameters[equipment] = []
        
        if state == 'down':
            if parameter not in self.selected_parameters[equipment]:
                self.selected_parameters[equipment].append(parameter)
        else:
            if parameter in self.selected_parameters[equipment]:
                self.selected_parameters[equipment].remove(parameter)
        
        # Atualiza card_configs na tela Overview
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
        
        # Salva as alterações
        salvar_cards(overview_screen.card_configs)
        
        # Atualiza a tela Overview se estiver visível
        if self.gerenciador.current == "overview":
            self.gerenciador.get_screen("overview").genereate_cards()

    def on_screen_change(self, instance, screen_name):
        if screen_name == 'overview':
            if not self.navigation_bar:
                self.navigation_bar = NavigationBar(
                    screen_manager=self.gerenciador,
                    logout_callback=self.logout
                )
                # Garante que não adiciona duplicado
                if self.navigation_bar.parent:
                    self.root_layout.remove_widget(self.navigation_bar)

                self.navigation_bar.size_hint = (1, None)
                self.navigation_bar.height = dp(56)
                self.navigation_bar.pos_hint = {"x": 0, "y": 0}
                self.root_layout.add_widget(self.navigation_bar)

        else:
            if self.navigation_bar:
                self.root_layout.clear_widgets()
                self.root_layout.add_widget(self.gerenciador)
                self.navigation_bar = None

    def logout(self):
        delete_access_token()
        self.gerenciador.current = 'login'


if __name__ == '__main__':
    OceanStream().run()
