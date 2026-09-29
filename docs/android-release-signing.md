# Assinatura local do release Android

O OceanStream usa o identificador `org.oceanstream.oceanstream`. Para continuar
atualizando o aplicativo publicado, preserve o keystore e a identidade de
assinatura existentes. O spec permanece em `.wsl/buildozer.spec`.

O nome de keystore registrado é `evlmetocean.keystore` e o alias existente é
`evlmetocean`. O caminho local pode variar entre máquinas; use o caminho absoluto
para esse mesmo keystore. Não gere uma chave nova, não substitua o arquivo e não
altere o alias para seguir estas instruções.

## Variáveis de ambiente

O fluxo de assinatura do python-for-android utiliza estas quatro variáveis:

| Variável | Conteúdo local |
| --- | --- |
| `P4A_RELEASE_KEYSTORE` | Caminho absoluto para o keystore existente |
| `P4A_RELEASE_KEYALIAS` | Alias existente: `evlmetocean` |
| `P4A_RELEASE_KEYSTORE_PASSWD` | Senha existente do keystore |
| `P4A_RELEASE_KEYALIAS_PASSWD` | Senha existente do alias |

As entradas de nome de arquivo e alias preservadas no spec não substituem essas
variáveis. Não grave senhas no spec, na documentação ou em comandos literais
salvos no histórico do terminal.

## Configuração interativa local

Em uma sessão **Bash** no ambiente usado para o build Android (por exemplo,
Linux/WSL), leia as senhas sem eco na tela. Se estiver usando outro shell, abra
uma sessão Bash antes de executar o trecho abaixo:

```bash
set +x
read -r -p 'Caminho absoluto do keystore existente: ' P4A_RELEASE_KEYSTORE
export P4A_RELEASE_KEYSTORE
export P4A_RELEASE_KEYALIAS='evlmetocean'
read -r -s -p 'Senha do keystore: ' P4A_RELEASE_KEYSTORE_PASSWD
printf '\n'
export P4A_RELEASE_KEYSTORE_PASSWD
read -r -s -p 'Senha do alias: ' P4A_RELEASE_KEYALIAS_PASSWD
printf '\n'
export P4A_RELEASE_KEYALIAS_PASSWD
```

As respostas aos prompts não são comandos e não ficam no histórico normal do
Bash. Não use `env`, `printenv`, `set -x` ou comandos semelhantes para exibir as
credenciais. Elas ficam no ambiente da sessão e são herdadas pelos processos
iniciados nela; execute somente ferramentas confiáveis nessa sessão.

Um build futuro deve ser iniciado nessa mesma sessão para receber as variáveis.
Esta etapa de configuração não executa nenhum build nem valida a assinatura.
Ela também não atualiza ferramentas, dependências ou versões de SDK/NDK.

Ao terminar de usar o ambiente de assinatura, remova as variáveis da sessão:

```bash
unset P4A_RELEASE_KEYSTORE P4A_RELEASE_KEYALIAS
unset P4A_RELEASE_KEYSTORE_PASSWD P4A_RELEASE_KEYALIAS_PASSWD
```

## Arquivos locais e Git

Prefira manter o keystore em seu local seguro atual, fora do repositório. Não é
necessário movê-lo para aplicar esta configuração.

O `.gitignore` protege arquivos `*.keystore`, `*.jks`, `.env`, `.env.*`, `*.env`,
`*.env.*`, diretórios `.signing/` e `.release-secrets/`, além destes nomes:

- `signing.properties`, `keystore.properties`, `key.properties`;
- `signing.local.*`, `release-signing.local.*`;
- `release-credentials.*`, `release_credentials.*`.

Guarde qualquer outro arquivo que contenha credenciais de release fora do
repositório ou dentro de `.release-secrets/`. Nenhum arquivo com senhas é criado
por estas instruções. Um arquivo `.env` não é carregado automaticamente pelo
Buildozer apenas por existir.

O `.gitignore` filtra nomes e caminhos, não o conteúdo dos arquivos. Ele não
protege arquivos já rastreados e pode ser contornado por `git add -f`. Antes de
um commit futuro, revise os arquivos preparados para commit sem compartilhar
saídas que contenham segredos.

## Exposição anterior e continuidade das atualizações

As senhas removidas do spec continuam nos commits anteriores. Esta Fase 1 não
reescreve o histórico, não faz commit e não revoga as credenciais expostas.
A alteração da versão corrente só será registrada em um commit futuro.

A exposição anterior precisa ser avaliada separadamente, considerando quem
teve acesso ao repositório e ao keystore. Não substitua a chave para resolver
essa exposição sem avaliar o processo de assinatura e upload do aplicativo
publicado no Google Play.

Preservar o keystore, o alias e o identificador mantém os elementos de identidade
existentes. A configuração não comprova, por si só, que um artefato será aceito
pela loja: a assinatura e sua correspondência com o aplicativo publicado ainda
precisam ser verificadas em uma etapa futura autorizada.
