# 🎵 Adicionar Músicas

App para celular que manda links do YouTube para o robô de cadastro.
O robô roda no **GitHub Actions** (servidor grátis do GitHub) e faz o mesmo que o notebook do Colab:
pula vídeos curtos e já cadastrados, baixa, sobe pro Drive e cadastra no banco.

Você só precisa configurar isso **uma vez**.

---

## 1. Criar o repositório e subir os arquivos

1. No GitHub, crie um repositório novo (ex.: `adicionar-musicas`). Pode ser **público** (as senhas ficam
   nos *Secrets*, que ninguém vê).
2. Suba todos os arquivos desta pasta (menos o `Codigo.txt`, que tem a senha escrita nele).
3. Em **Settings → Pages**, em *Source* escolha **Deploy from a branch**, branch `main`, pasta `/ (root)`.
   Em 1–2 minutos o app estará em `https://SEU-USUARIO.github.io/adicionar-musicas/`.

## 2. Permitir o robô acessar seu Google Drive (uma vez só)

No Colab o login era automático. Aqui o robô precisa de uma "chave" permanente:

1. Acesse <https://console.cloud.google.com/>, crie um projeto e ative a **Google Drive API**.
2. Em **APIs e serviços → Tela de consentimento OAuth**: tipo *Externo*, preencha o básico e
   adicione seu e-mail como usuário de teste. Depois clique em **Publicar app** (status *Em produção*).
   > ⚠️ Se deixar em *Teste*, a chave expira a cada 7 dias.
3. Em **Credenciais → Criar credenciais → ID do cliente OAuth**:
   - Tipo: **Aplicativo da Web**
   - URI de redirecionamento autorizado: `https://developers.google.com/oauthplayground`
   - Anote o **Client ID** e o **Client secret**.
4. Abra <https://developers.google.com/oauthplayground>:
   - Clique na engrenagem ⚙️ → marque **Use your own OAuth credentials** → cole o Client ID e o Secret.
   - Na lista da esquerda, digite no campo: `https://www.googleapis.com/auth/drive` → **Authorize APIs**.
   - Entre com sua conta (vai aparecer "app não verificado" → *Avançado → Continuar*).
   - Clique em **Exchange authorization code for tokens** e copie o **Refresh token**.

## 3. Cadastrar os segredos no repositório

No repositório: **Settings → Secrets and variables → Actions → New repository secret**.
Crie um para cada linha:

| Nome | Valor |
|---|---|
| `API_URL` | `https://cantajunto.online/api/migracao_drive.php` |
| `API_SENHA` | a senha da sua API |
| `DRIVE_PASTA_ID` | ID da pasta do Drive (o final do link da pasta) |
| `GOOGLE_CLIENT_ID` | do passo 2 |
| `GOOGLE_CLIENT_SECRET` | do passo 2 |
| `GOOGLE_REFRESH_TOKEN` | do passo 2 |
| `YT_COOKIES` | conteúdo inteiro do seu `cookies.txt` do YouTube (o mesmo que usava no Colab) |

Opcional: em **Variables** você pode criar `TEMPO_MINIMO_SEGUNDOS` (padrão 90).

## 4. Criar o token do app

1. GitHub → foto → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. *Repository access*: **Only select repositories** → escolha `adicionar-musicas`.
3. *Permissions → Repository permissions → Actions*: **Read and write**.
4. Escolha uma validade longa e gere. Copie o token (`github_pat_...`).

## 5. Instalar no celular

1. Abra `https://SEU-USUARIO.github.io/adicionar-musicas/` no **Chrome** do celular.
2. Cole o token, confira o repositório e toque em **Salvar**.
3. Menu ⋮ → **Instalar app** (ou "Adicionar à tela inicial").

## Como usar

- **Mais rápido:** no app do YouTube, toque em **Compartilhar → Músicas**. O link já cai no app.
  Ative "Enviar sozinho quando eu compartilhar" nas configurações ⚙️ para nem precisar tocar em Enviar.
- Ou abra o app, cole um link de vídeo, playlist ou canal (ou vários, um por linha) e toque em **Enviar**.
- A lista mostra o andamento. "Ver detalhes" abre o log completo e um resumo de cada música.

> O "Compartilhar" direto funciona no Android (Chrome). No iPhone, use o botão Colar.

## Problemas comuns

- **"Falha ao baixar" em tudo** → o YouTube bloqueou o servidor. Exporte um `cookies.txt` novo
  (de preferência numa aba anônima logada, e feche a aba depois) e atualize o secret `YT_COOKIES`.
- **Erro no Drive (invalid_grant)** → o refresh token expirou. Refaça o passo 2.4
  (e confira se o app está *Em produção*).
- **Playlists muito grandes**: cada execução pode durar até 6 h. Com a pausa de ~90 s entre vídeos,
  isso dá umas 200 músicas por envio; mande o resto em outro envio (as já cadastradas são puladas).
