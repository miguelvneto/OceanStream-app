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
source.exclude_dirs = .git,.github,.wsl,.venv,venv,env,.buildozer,bin,docs,.signing,.release-secrets,__pycache__,.idea,.vscode,.vs,build,dist,tmp,temp,.pytest_cache,.mypy_cache,.ruff_cache,.tox,.nox,tests
source.exclude_patterns = */venv/*,*/env/*,*/__pycache__/*,comandos,*/comandos,p4a_env_vars.txt,*/p4a_env_vars.txt,*.keystore,*.jks,.env,.env.*,*/.env,*/.env.*,signing.properties,*/signing.properties,keystore.properties,*/keystore.properties,key.properties,*/key.properties,signing.local.*,*/signing.local.*,release-signing.local.*,*/release-signing.local.*,release-credentials.*,*/release-credentials.*,release_credentials.*,*/release_credentials.*,oceanstream.jwt,*/oceanstream.jwt,*~,*.bak,*.orig,*.rej,*.tmp,*.temp,*.swp,*.swo,*.pyc,*.pyo,*.code-workspace,*.sublime-project,*.sublime-workspace,*.iml

# Arquivo principal
source.main = main.py

# Inclui todo o conteúdo da pasta res (se você usa imagens lá)
presplash.filename = res/logo.png
#android.presplash_color = #55E6C9

# Versão do app
version.regex = ^__version__ = ['"]([0-9]+(?:\.[0-9]+)*)['"]
version.filename = app_version.py

# Ícone do app (opcional)
icon.filename = res/logo.png

# Linguagem requerida
requirements = python3,kivy,kivymd,plyer,requests,pyjwt,pillow,certifi,urllib3,chardet,idna,pyjnius

# Orientação de tela
orientation = portrait

# Permissões necessárias
android.permissions = INTERNET

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

# Configure signing locally with P4A_RELEASE_* environment variables.
# See docs/android-release-signing.md.
fullscreen = 0
android.enable_optimizations = True
log_level = 2
android.allow_backup = True
android.hardwareAccelerated = 1
