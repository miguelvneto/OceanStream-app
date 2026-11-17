# OceanStream iOS 1.6 — Identidade visual

Recursos utilizados na versão iOS 1.6:

- AppIcon.appiconset: ícones oficiais da Environlink.
- EnvironlinkLaunch.imageset: logotipo utilizado na abertura.
- Launch Screen.storyboard: tela de lançamento nativa.

Ao gerar um novo projeto com kivy-ios:

1. Copiar os dois conjuntos de imagens para Images.xcassets.
2. Substituir o storyboard de lançamento pelo arquivo versionado.
3. Configurar CFBundleDisplayName e CFBundleName como OceanStream.
4. Manter o Bundle ID br.com.oceanstream.
5. Definir a versão 1.6 e o build apropriado.

A splash animada do Kivy permanece desativada.
A navigation bar deve ser inicializada na entrada direta pelo Overview.
