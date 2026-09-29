# Build Android do OceanStream

## Estrutura e diretório de execução

Execute os comandos a partir da raiz do repositório. O único `buildozer.spec`
fica junto de `main.py`, `navigation_bar.py`, `paginas/`, `res/` e `data/`.
Na Fase 2, o arquivo foi movido de `.wsl/buildozer.spec` sem alterar seu conteúdo.

Com `source.dir = .`, a raiz contém os fontes. `icon.filename` e
`presplash.filename` continuam apontando para `res/logo.png`. Os caminhos
`paginas/*.kv`, `res/*` e `data/cards.json` usados pelo aplicativo permanecem
inalterados. Não execute o build dentro de `.wsl` nem mantenha outra cópia do spec.

O cache local padrão será `.buildozer/` e os artefatos ficarão em `bin/`.
Esses diretórios são ignorados pelo Git. Não apague nem migre caches de outro
ambiente sem antes registrar a cadeia usada no último build válido.

## Configurações preservadas

Permanecem API 35, target declarado 35, minAPI 21, NDK 25b, arquiteturas
`arm64-v8a,armeabi-v7a` e versão do aplicativo. As declarações de Python, Kivy e
KivyMD e as demais opções do spec permanecem iguais, exceto pelos filtros,
dependências e permissões descritos abaixo para a Fase 4.
Nenhuma ferramenta foi atualizada e nenhum build foi executado nesta fase.

A assinatura continua usando as mesmas variáveis e identidade descritas em
[android-release-signing.md](android-release-signing.md). O caminho absoluto
do keystore não depende da posição do spec. Não gere ou substitua chaves.

## Higiene do empacotamento (Fase 4)

O `.gitignore` não filtra o pacote Android. O spec mantém
`source.include_exts = py,png,jpg,kv,atlas,json` e acrescenta exclusões explícitas
de ambientes virtuais, caches, documentação, artefatos, arquivos temporários,
configuração de editores e credenciais locais. As listas `source.exclude_dirs`
e `source.exclude_patterns` ocupam uma linha cada, separadas por vírgulas:
o Buildozer 1.5.0 lê esses valores com `split(',')` e remove espaços de cada item.

`source.exclude_dirs` cobre diretórios relativos à raiz; os padrões também
bloqueiam `venv/`, `env/` e `__pycache__/` aninhados. Diretórios e arquivos ocultos
já são descartados pelo Buildozer 1.5.0. Arquivos sem extensão podem passar pelo
filtro de extensões, por isso `comandos` tem exclusão explícita.

Os filtros preservam os 52 arquivos selecionados na árvore atual: quatro na
raiz, sete em `paginas/`, 38 em `res/` e três em `data/`. Permanecem incluídos
`main.py`, `res/logo.png` e `data/cards.json`. `.env.example` pode ser versionado,
mas fica fora do pacote. Credenciais com nomes arbitrários dentro de um JSON ou
Python permitido ainda podem ser incluídas; mantenha segredos fora dos fontes.

Uma cópia local de `p4a_env_vars.txt` fica excluída dos fontes. O p4a também gera
um arquivo desse nome durante o empacotamento: no APK antigo inspecionado, seus
87 bytes continham apenas `P4A_IS_WINDOWED`, `KIVY_ORIENTATION`,
`P4A_NUMERIC_VERSION` e `P4A_MINSDK`. Esse metadado pode continuar no APK;
sua presença, isoladamente, não indica vazamento de credenciais.

### Dependências e permissões

- Removido `kivy_garden.matplotlib`: não há import ativo e `plot_graph()` é vazio.
- Substituído `jnius` por `pyjnius`, nome da receita; o módulo Python é `jnius`.
- Adicionado `pillow`, dependência do KivyMD 1.2.0, cujo pacote de seletores
  importa o seletor de cores que usa PIL. Sua receita nativa exige validação
  no ambiente Android antes do primeiro build.
- Mantidos `certifi`, `urllib3`, `idna` e `chardet`. A receita Kivy 2.3.0 do p4a
  consultado declara essas dependências; falta de import direto não justifica
  removê-las. As versões continuam sem fixação no spec.
- Mantida `INTERNET`. Removidas `READ_EXTERNAL_STORAGE` e
  `WRITE_EXTERNAL_STORAGE`: o fluxo normal grava JWT e configurações em
  `App.user_data_dir`, sem uso identificado de armazenamento compartilhado.
- Removida a declaração `android.manifest_attributes` com
  `requestLegacyExternalStorage`. No Android 11 ou superior, com target 30 ou
  superior, essa flag é ignorada. Os fallbacks de armazenamento existentes
  ainda precisam de teste em dispositivo, inclusive em Android antigo.

Referências de implementação: receitas
[Kivy](https://github.com/kivy/python-for-android/blob/v2024.01.21/pythonforandroid/recipes/kivy/__init__.py),
[Pillow](https://github.com/kivy/python-for-android/blob/v2024.01.21/pythonforandroid/recipes/Pillow/__init__.py)
e [geração de metadados](https://github.com/kivy/python-for-android/blob/v2024.01.21/pythonforandroid/bootstraps/common/build/build.py)
do p4a v2024.01.21, sem afirmar que esse commit produziu o último release;
[armazenamento no Android 11](https://developer.android.com/about/versions/11/privacy/storage).

## Versionamento e atualização (Fase 5 parcial)

A integração de `app_version.py` está pendente da escolha explícita da versão.
O módulo contém `__version__ = None` e ainda não é consumido. Continuam
`version = 0.3.4` no spec e `VERSAO_ATUAL = '0.4.1'` no aplicativo; não publicar
supondo que essa divergência já foi resolvida. O comparador e o tratamento de
respostas/lojas foram protegidos sem escolher o número de release.

`tests/` foi acrescentado às exclusões para não empacotar os testes Python.
`app_version.py` e `update_utils.py` são selecionados pelos filtros existentes.
Consulte [app-updates.md](app-updates.md) para o contrato, testes e pendências.

## Inventário obrigatório antes do primeiro build

A posição do spec padroniza a execução, mas não garante reprodução exata dos
binários. As versões do último ambiente Android válido ainda precisam ser
identificadas. Não instale versões atuais por suposição nem trate o
`requirements.txt` desktop como um lock do build Android.

Registre, sem credenciais, o commit do aplicativo e estes dados do ambiente real:

- Sistema operacional, arquitetura e ambiente Linux/WSL utilizado.
- Python do ambiente de build, Buildozer, Cython e JDK.
- Commit e eventuais modificações locais do python-for-android.
- Python embarcado, Kivy, KivyMD e versões das receitas efetivamente utilizadas.
- SDK instalado, Build Tools, revisão do NDK, Gradle e Android Gradle Plugin.
- Caminhos de ferramentas/caches e comandos do último build válido.

O Python que executa o Buildozer e o Python embarcado pelo p4a são componentes
distintos. O spec não fixa todas essas versões. Não há inventário suficiente
neste repositório para preencher os valores faltantes com segurança.

## Verificações sem build

Na raiz, confira os recursos e o estado do repositório:

```bash
test -f buildozer.spec
test -f main.py
test -f res/logo.png
test -f data/cards.json
test -d paginas
test -d res
test -d data
git diff --check
git status
```

No ambiente Android já utilizado, consulte as versões sem instalar pacotes:

```bash
python --version
python -m pip show buildozer Cython
java -version
```

Consulte o commit do p4a e os demais componentes nos caminhos reais desse ambiente.
Evite compartilhar logs ou listagens de ambiente que exponham credenciais.

## Primeiro build debug: etapa futura autorizada

Mesmo um build debug pode baixar dependências, atualizar componentes do SDK ou
obter outro commit de p4a se o cache estiver ausente. Antes de executar, confirme
como preservar a cadeia existente e impedir atualizações implícitas. Não execute
`buildozer android update`, instalações ou atualizações de pacotes nesta fase.

Somente após essa validação e autorização, execute na raiz, em Linux/WSL:

```bash
env -u P4A_RELEASE_KEYSTORE \
    -u P4A_RELEASE_KEYALIAS \
    -u P4A_RELEASE_KEYSTORE_PASSWD \
    -u P4A_RELEASE_KEYALIAS_PASSWD \
    buildozer android debug
```

As variáveis de release são retiradas apenas do processo debug. Confira a saída
em `bin/`, as versões efetivamente usadas e a inclusão dos recursos no pacote.
Um build concluído não substitui teste de inicialização, telas e acesso à API
em dispositivo. A aceitação nas lojas e a assinatura de release são etapas
separadas, ainda não validadas.

Inspecione também o APK/AAB produzido: confirme os recursos necessários, o
manifesto final e a ausência de ambientes virtuais, `comandos`, documentação e
credenciais locais. Distinga o `p4a_env_vars.txt` gerado pelo p4a de cópias locais.
A verificação dos filtros sem build não substitui essa inspeção do artefato.

## Problemas conhecidos, mantidos para análise posterior

- `android.arch` é legado; `android.sdk` é obsoleto e ignorado.
- No Buildozer 1.5.0 consultado, não há consumo identificado de `source.main`,
  `android.target_api`, `android.build_tools_version`, `android.enable_optimizations`,
  `android.hardwareAccelerated` ou das entradas
  `android.release_keystore`/`android.release_alias`. A versão real deve ser conferida.
- `log_level` está em `[app]`, em vez de `[buildozer]`.
- `version = 0.3.4` difere de `VERSAO_ATUAL = '0.4.1'` no código.
- Dependências não estão fixadas no spec; ainda é necessário recuperar o ambiente
  para impedir mudanças implícitas de versão no primeiro build.
- Compatibilidade nativa, páginas de 16 KB e requisitos das lojas não estão
  comprovados pela simples movimentação do spec.

Referências usadas para conferir as opções, sem prescrever atualização de versão:
[Buildozer 1.5.0](https://github.com/kivy/buildozer/blob/1.5.0/buildozer/__init__.py) e
[target Android](https://github.com/kivy/buildozer/blob/1.5.0/buildozer/targets/android.py).
