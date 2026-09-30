# Atualizações do OceanStream — Fase 5

## Fonte única de versão comercial — Fase 5B

A versão comercial definida para o próximo release é **1.6**. `app_version.py`
é a fonte única: `main.py` importa `__version__` como `VERSAO_ATUAL`, e o
Buildozer lê a mesma declaração por `version.regex` e `version.filename`.
A declaração deve permanecer na primeira linha do módulo: o regex começa com
`^` e o Buildozer 1.5.0 usa `re.search` sem modo multilinha.

Android e iOS passam a compartilhar a versão comercial **1.6** a partir desse
release. O projeto Xcode externo não foi alterado; sua Version deverá ser
sincronizada com essa fonte na preparação do release iOS.

Dados das lojas confirmados pelo responsável pelo release:

- Android publicado/testado: versionName **0.3.4**, versionCode **1021304**,
  target SDK **35**, min SDK **21**.
- iOS publicado: Version **1.5**, Build **1.1**, Bundle ID **br.com.oceanstream**.

O versionCode Android é independente da versão comercial e deverá ser
**maior que 1021304**. Nenhum próximo valor foi definido no spec; a decisão
será feita na máquina Android após conferir a cadeia real de Buildozer/p4a.
Não presumir que a geração automática a partir de 1.6 produzirá um código adequado.

O Build iOS também é independente e deverá ser **maior que 1.1**. Nenhum valor
novo foi definido e o Bundle ID permanece preservado. `APP_STORE_ID` continua
`None`, pendente do Apple ID numérico real.

## Contrato aceito

O endpoint e a autenticação permanecem iguais. `api_lastestVersion()` faz POST
para `lastestVersion/android` no Android/Windows, `lastestVersion/ios` no iOS e
`lastestVersion/` nas demais plataformas, com o timeout existente de 25 segundos.

O corpo pode ser um objeto JSON com `version` ou `latest_version`, uma JSON string
ou texto simples. Em objetos, usa-se o primeiro campo válido nessa ordem.
Valores de campos JSON não textuais e respostas inválidas retornam None.
Para o corpo bruto ambíguo `0.4`, valida-se o texto original como versão com
ponto, sem converter o número produzido pelo JSON. Assim, `0.4` é aceito, mas
`42`, `true`, `null`, `[0,4]` e `{"version":0.4}` são rejeitados. O corpo não é registrado
nos logs de status HTTP. Isso descreve o contrato aceito pelo cliente, sem afirmar
quais formatos o backend realmente envia.

`update_utils.py` usa apenas biblioteca padrão. Aceita componentes numéricos ASCII
separados por pontos, prefixo opcional v/V, espaços externos e um par de aspas
externas correspondente. Componentes ausentes valem zero: 0.4.1 e 0.4.1.0 são
iguais; 0.4.1.1 é maior que 0.4.1. A comparação é numérica, não textual.

Versões têm limite de 256 caracteres e corpos interpretados, 4096 caracteres.
Esses limites são aplicados após receber a resposta, não limitam o download HTTP.
Sinais, sufixos, componentes vazios, tipos não textuais e aspas sem fechamento
são inválidos. Qualquer lado inválido resulta em sem atualização. Os formatos
aceitos para comparação não são uma garantia de validade nas lojas.

## Interface e lojas

Falhas na comparação, construção ou abertura do diálogo permitem seguir para o
overview. O fechamento programático remove o callback antes de dismiss; a saída
é agendada no máximo uma vez por consulta. Cada chamada cria um identificador;
só o primeiro resultado da consulta vigente é consumido. Resultados antigos,
repetidos ou posteriores ao fechamento não reabrem o diálogo. Botões e saídas
agendadas de consultas antigas também são ignorados. Uma consulta nova pode
substituir a anterior e funcionar normalmente. Os caminhos de login, splash e sessão válida
não foram centralizados. A splash ainda pode ir diretamente ao overview.

Android mantém https://play.google.com/store/apps/details?id=org.oceanstream.oceanstream.
O fallback desktop para a Play Store foi preservado.

`APP_STORE_ID = None` impede convite de atualização no iOS e abertura de placeholders.
Após obter o ID real, configurar uma string numérica positiva (até 20 dígitos)
em `update_utils.py`. O código gera os destinos nativo e HTTPS; exceção ou retorno
False do navegador aciona o próximo destino. O ID é público e não é uma credencial.
Mesmo se todos os destinos falharem, o aplicativo continua para o overview.

## Verificação sem build

```bash
python3 -B -m unittest discover -s tests -v
git diff --check
```

Os testes exercitam funções puras e os callbacks reais de main.py extraídos por
AST, com mocks de UI, HTTP, Clock e navegador. Não importam Kivy, não acessam o
backend e não abrem lojas. `tests/` está excluído do pacote Android; os módulos
novos na raiz são selecionados pela extensão py.

Ainda será necessário testar em dispositivo o diálogo e a abertura das lojas.
Nenhum build, atualização de ferramenta ou alteração de layout foi realizado.
