todos os comandos estão sendo executados no WSL (ubuntu)

 - comando utilizado para gerar a chave auto assinada:
keytool -genkey -v -keystore evlmetocean.keystore -alias evlmetocean -keyalg RSA -keysize 2048 -validity 10000
 - a chave em uso está presente nesta mesma pasta sob o nome "evlmetocean.keystore" | a senha é "JRuano" (sem as aspas)

 - comando para incorporar a assinatura ao .aab:
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore evlmetocean.keystore bin/oceanstream-0.1-arm64-v8a_armeabi-v7a-release.aab evlmetocean
 - comando para verificar se o .aab possui assinaturas:
jarsigner -verify -verbose -certs bin/oceanstream-0.1-arm64-v8a_armeabi-v7a-release
