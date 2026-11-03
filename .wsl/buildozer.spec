[app]

# Nome do seu app
title = OceanStream

# Nome do pacote
package.name = oceanstream

# Nome da organização
package.domain = org.oceanstream

# Fonte principal
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf


presplash.filename = res/logo.png

# Versão do app
version = 0.4.1

# Ícone do app (opcional)
icon.filename = res/logo.png

# Linguagem requerida
requirements = python3,kivy,kivymd==1.2.0,materialyoucolor==3.0.4,pillow,plyer,requests,pyjwt,certifi,urllib3,chardet,idna,pyjnius

# Orientação de tela
orientation = portrait

# Permissões necessárias
android.permissions = INTERNET

android.archs = arm64-v8a

android.minapi = 24
android.api = 36
fullscreen = 1
android.enable_optimizations = True
log_level = 2
android.allow_backup = True