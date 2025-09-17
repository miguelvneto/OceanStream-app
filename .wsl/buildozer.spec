[app]

# Nome do seu app
title = OceanStream

# Nome do pacote
package.name = oceanstream

# Nome da organização
package.domain = org.oceanstream

# Fonte principal
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

# Arquivo principal
source.main = main.py

# Inclui todo o conteúdo da pasta res (se você usa imagens lá)
presplash.filename = res/logo.png
#android.presplash_color = #55E6C9

# Versão do app
version = 0.3.2

# Ícone do app (opcional)
icon.filename = res/logo.png

# Linguagem requerida
requirements = python3,kivy,kivymd,plyer,requests,pyjwt,kivy_garden.matplotlib,certifi,urllib3,chardet,idna,jnius

# Orientação de tela
orientation = portrait

# Permissões necessárias
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Arquitetura suportada
android.arch = arm64-v8a,armeabi-v7a

# Configurações específicas
android.minapi = 21
android.sdk = 35
android.ndk = 25b
android.api = 35
android.build_tools_version = 35.0.0
android.target_api = 35

# Se quiser melhorar o tamanho do APK:
# android.enable_optimizations = True

# Indica ao buildozer para incluir recursos externos (opcional)
# include_exts = kv,png,jpg,atlas,json

# (android) The name of the keystore file to use for signing the app
android.release_keystore = evlmetocean.keystore

# (android) The alias to use when signing the app
android.release_alias = evlmetocean

# (android) The password for the keystore
android.release_keystore_passwd = JRuano

# (android) The password for the alias
android.release_alias_passwd = JRuano

fullscreen = 1
android.enable_optimizations = True
log_level = 2
android.allow_backup = True
android.hardwareAccelerated = 1

# Para Android 10+ com scoped storage
android.manifest_attributes = android:requestLegacyExternalStorage="true"