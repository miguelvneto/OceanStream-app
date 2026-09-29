# Build Android do OceanStream

## Estrutura e diretório de execução

Execute os comandos a partir da raiz do repositório. O único `buildozer.spec`
fica junto de `main.py`, `navigation_bar.py`, `paginas/`, `res/` e `data/`.
O arquivo foi movido de `.wsl/buildozer.spec` sem alterar seu conteúdo.

Com `source.dir = .`, a raiz contém os fontes. `icon.filename` e
`presplash.filename` continuam apontando para `res/logo.png`. Os caminhos
`paginas/*.kv`, `res/*` e `data/cards.json` usados pelo aplicativo permanecem
inalterados. Não execute o build dentro de `.wsl` nem mantenha outra cópia do spec.

O cache local padrão será `.buildozer/` e os artefatos ficarão em `bin/`.
Esses diretórios são ignorados pelo Git. Não apague nem migre caches de outro
ambiente sem antes registrar a cadeia usada no último build válido.

## Configurações preservadas

Permanecem API 35, target declarado 35, minAPI 21, NDK 25b, arquiteturas
`arm64-v8a,armeabi-v7a`, permissões, dependências, versão e opções do spec.
Nenhuma ferramenta foi atualizada e nenhum build foi executado nesta organização.

A assinatura continua usando as mesmas variáveis e identidade descritas em
[android-release-signing.md](android-release-signing.md). O caminho absoluto
do keystore não depende da posição do spec. Não gere ou substitua chaves.

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

## Problemas conhecidos, mantidos para análise posterior

- `android.arch` é legado; `android.sdk` é obsoleto e ignorado.
- No Buildozer 1.5.0 consultado, não há consumo identificado de `source.main`,
  `android.target_api`, `android.build_tools_version`, `android.enable_optimizations`,
  `android.hardwareAccelerated`, `android.manifest_attributes` ou das entradas
  `android.release_keystore`/`android.release_alias`. A versão real deve ser conferida.
- `log_level` está em `[app]`, em vez de `[buildozer]`.
- `version = 0.3.4` difere de `VERSAO_ATUAL = '0.4.1'` no código.
- Dependências não estão fixadas no spec; `jnius` precisa ser confrontado com a
  receita `pyjnius`; gráficos sem uso e inclusão de Pillow precisam de revisão.
- Permissões de armazenamento externo não têm uso identificado;
  `requestLegacyExternalStorage` não resolve armazenamento para o target atual.
- Compatibilidade nativa, páginas de 16 KB e requisitos das lojas não estão
  comprovados pela simples movimentação do spec.

O `.gitignore` não filtra o pacote Android. Mantenha credenciais fora da árvore
de fontes ou nos diretórios ocultos definidos na documentação de assinatura.
Prefira ambiente virtual externo ou `.venv`: diretórios não ocultos como `venv/`
podem ter arquivos selecionados pelo Buildozer apesar de ignorados pelo Git.
Nenhum filtro de empacotamento foi alterado nesta etapa.

Referências usadas para conferir as opções, sem prescrever atualização de versão:
[Buildozer 1.5.0](https://github.com/kivy/buildozer/blob/1.5.0/buildozer/__init__.py) e
[target Android](https://github.com/kivy/buildozer/blob/1.5.0/buildozer/targets/android.py).
