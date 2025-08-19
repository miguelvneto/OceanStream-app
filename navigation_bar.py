from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle

class NavigationBar(MDBoxLayout):
    def __init__(self, screen_manager, logout_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.screen_manager = screen_manager
        self.logout_callback = logout_callback

        self.toolbar = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint_y=None,
            height=dp(56),
            padding=[dp(10), dp(10)]
        )

        with self.toolbar.canvas.before:
            Color(0.02, 0.58, 0.61, 1)
            self.bg_rect = RoundedRectangle(
                size=self.toolbar.size,
                pos=self.toolbar.pos,
                radius=[(dp(36), dp(36)), (dp(36), dp(36)), (0, 0), (0, 0)]
            )
            self.toolbar.bind(size=self.update_bg, pos=self.update_bg)

        # LOGO fixada ao topo da barra
        self.logo_container = FloatLayout(size_hint=(1, None), height=dp(100))
        self.expand_button = MDIconButton(
            icon="res/logo_circulada.png",
            size_hint=(None, None),
            size=(dp(80), dp(80)),
            icon_size=dp(80),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            pos_hint={"center_x": 0.5},
            y=self.toolbar.height - dp(40),  # posição inicial (ajustada via bind abaixo)
            on_release=self.toggle_toolbar
        )
        self.logo_container.add_widget(self.expand_button)
        self.toolbar.add_widget(self.logo_container)

        # atualiza a posição da logo conforme altura da barra
        self.toolbar.bind(height=self.update_logo_position)

        self.options_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=0
        )

        self.options_icons_box = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(80),
            spacing=dp(10)
        )

        options = [
            {"text": "Configuração", "icon": "cog", "screen": "configuracao"},
            {"text": "Overview", "icon": "information", "screen": "overview"},
            {"text": "Equipamento", "icon": "access-point", "screen": "equipamento"},
        ]

        for option in options:
            option_box = BoxLayout(
                orientation="vertical",
                size_hint=(1, None),
                width=dp(80),
                height=dp(80),
                spacing=dp(5),
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            )

            icon_size = dp(60) if option["text"] in ["Configuração", "Overview", "Equipamento"] else dp(32)

            button = MDIconButton(
                icon=option["icon"],
                icon_size=icon_size,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_release=lambda x, screen=option["screen"]: self.switch_to_screen(screen),
                pos_hint={"center_x": 0.5}
            )

            label = Label(
                text=option["text"],
                font_size=dp(12),
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(20),
                color=(1, 1, 1, 1),
                pos_hint={"center_x": 0.5}
            )

            option_box.add_widget(button)
            option_box.add_widget(label)
            self.options_icons_box.add_widget(option_box)

        self.logout_button = MDRaisedButton(
            text="Logout",
            size_hint=(None, None),
            size=(dp(100), dp(36)),
            md_bg_color=(0.2, 0.6, 0.8, 1),
            text_color=(1, 1, 1, 1),
            pos_hint={"center_x": 0.5},
            on_release=self.logout
        )

        self.toolbar.add_widget(self.options_box)
        self.add_widget(self.toolbar)

    def toggle_toolbar(self, instance):
        if self.options_box.height == 0:
            self.options_box.add_widget(self.options_icons_box)
            self.options_box.add_widget(self.logout_button)

            anim_toolbar = Animation(height=dp(206), d=0.3)
            anim_options = Animation(height=dp(150), d=0.3)
        else:
            anim_toolbar = Animation(height=dp(56), d=0.3)
            anim_options = Animation(height=0, d=0.3)
            self.options_box.clear_widgets()

        anim_toolbar.start(self.toolbar)
        anim_options.start(self.options_box)

    def update_logo_position(self, instance, height_value):
        self.expand_button.y = height_value - (self.expand_button.height / 2)

    def update_bg(self, *args):
        self.bg_rect.size = self.toolbar.size
        self.bg_rect.pos = self.toolbar.pos

    def switch_to_screen(self, screen_name):
        if self.screen_manager.has_screen(screen_name):
            self.toggle_toolbar(None)
            self.screen_manager.current = screen_name
        else:
            print(f"Tela '{screen_name}' não encontrada.")

    def logout(self, instance):
        self.toggle_toolbar(instance)
        self.logout_callback()
        self.screen_manager.current = 'login'
