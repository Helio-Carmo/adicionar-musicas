# ==========================================
# 🤖 ROBÔ DE CADASTRO LITE (TEMPO, DUPLICIDADE E ARTISTA)
# Versão GitHub Actions do notebook do Colab.
# Configuração vem dos Secrets do repositório (ver LEIA-ME.md).
# ==========================================

import os
import sys
import time
import random
import re
import requests
import yt_dlp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from limpeza import artista_e_titulo

# ================= CONFIGURAÇÕES =================
URL_API = os.environ["API_URL"]
SENHA_API = os.environ["API_SENHA"]
CABECALHO_API = {"X-Migracao-Senha": SENHA_API}  # senha no cabeçalho, fora da URL
PASTA_DRIVE_ID = os.environ["DRIVE_PASTA_ID"]
TEMPO_MINIMO_SEGUNDOS = int(os.environ.get("TEMPO_MINIMO_SEGUNDOS") or 90)
# Pausa entre um download e outro (anti-bloqueio do YouTube), igual ao --sleep-interval do Colab
PAUSA_MIN, PAUSA_MAX = 90, 100
COOKIES = "cookies.txt" if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0 else None
# =================================================

FORMATO = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
MIMETYPES = {"mp4": "video/mp4", "webm": "video/webm", "mkv": "video/x-matroska"}
resumo = []  # (status, titulo, detalhe) para o relatório final


def conectar_drive():
    creds = Credentials(
        None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def opcoes_base():
    opts = {"quiet": True, "no_warnings": True}
    if COOKIES:
        opts["cookiefile"] = COOKIES
    return opts


def mapear_videos(link):
    """Retorna (videos, is_playlist, nome_pai). Abre as abas de canal (Vídeos, Shorts, Lives)."""
    with yt_dlp.YoutubeDL({**opcoes_base(), "extract_flat": True}) as ydl:
        info = ydl.extract_info(link, download=False)
        nome_pai = info.get("uploader") or info.get("channel") or info.get("title") or "Desconhecido"

        if "entries" not in info:
            return [info], False, nome_pai

        videos = []
        for e in info["entries"]:
            if not e:
                continue
            # Link de canal sem aba: cada "entrada" é uma aba (playlist) e não um vídeo
            if e.get("_type") == "playlist" or e.get("ie_key") == "YoutubeTab":
                sub = ydl.extract_info(e["url"], download=False)
                videos.extend(x for x in sub.get("entries", []) if x)
            else:
                videos.append(e)
        return videos, True, nome_pai


def ja_cadastrado(yt_id):
    try:
        res = requests.get(URL_API, params={"action": "verificar", "yt_id": yt_id}, headers=CABECALHO_API, timeout=30)
        return res.json().get("existe") == True
    except Exception:
        print("   ⚠️ Erro ao verificar duplicidade. Tentando baixar mesmo assim...")
        return False


def cadastrar(dados_post, yt_id):
    """Cadastra no banco tentando até 3 vezes (queda de conexão). Antes de repetir, confere se já entrou."""
    for tentativa in range(3):
        try:
            res = requests.post(URL_API, params={"action": "cadastrar"}, headers=CABECALHO_API, data=dados_post, timeout=60)
            res.raise_for_status()
            return
        except Exception:
            if tentativa == 2:
                raise
            time.sleep(10)
            if ja_cadastrado(yt_id):
                return


def baixar(yt_id):
    """Baixa o vídeo e devolve o caminho do arquivo (ou None)."""
    opts = {
        **opcoes_base(),
        "format": FORMATO,
        "merge_output_format": "mp4",
        "outtmpl": "%(id)s.%(ext)s",
        "sleep_interval_requests": 2,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={yt_id}", download=True)
            baixados = info.get("requested_downloads") or []
            caminho = baixados[0].get("filepath") if baixados else ydl.prepare_filename(info)
            return caminho if caminho and os.path.exists(caminho) else None
    except Exception as err:
        print(f"   ↳ {err}")
        return None


def processar_link(link, artista_fixo, drive, estado):
    print(f"\n🔎 Mapeando os vídeos de: {link}")
    try:
        videos, is_playlist, nome_pai = mapear_videos(link)
    except Exception as err:
        print(f"❌ Não consegui ler esse link: {err}")
        resumo.append(("❌", link, "Link inválido ou bloqueado"))
        return

    print(f"🎯 Total de vídeos mapeados inicialmente: {len(videos)}\n")

    for i, v in enumerate(videos, 1):
        yt_id = v.get("id")
        titulo = v.get("title") or yt_id
        duracao = v.get("duration")
        canal = v.get("uploader") or v.get("channel")

        if not yt_id:
            continue

        print("--------------------------------------------------")

        if is_playlist and duracao is not None and duracao < TEMPO_MINIMO_SEGUNDOS:
            print(f"⏭️ PULANDO ({i}/{len(videos)}): {titulo}")
            print(f"   Motivo: Muito curto ({duracao}s). Provável propaganda.")
            resumo.append(("⏭️", titulo, f"Muito curto ({duracao}s)"))
            continue

        print(f"🎵 PROCESSANDO ({i}/{len(videos)}): {titulo}")

        if ja_cadastrado(yt_id):
            print("   ⚠️ PULANDO: Esta música já está cadastrada no seu sistema!")
            resumo.append(("🔁", titulo, "Já cadastrada"))
            continue

        # ARTISTA: o informado no envio > o encontrado pelo título > canal do vídeo > dono da playlist/canal
        # TÍTULO: só o nome da música, sem "Karaoke", canal ou artista
        artista_achado, titulo_limpo = artista_e_titulo(titulo, canal, artista_fixo)
        artista_yt = artista_achado or canal or nome_pai
        print(f"   🎤 Artista: {artista_yt} | Música: {titulo_limpo} | Canal: {canal} | ID: {yt_id}")

        if estado["baixou_algum"]:
            pausa = random.uniform(PAUSA_MIN, PAUSA_MAX)
            print(f"   😴 Aguardando {pausa:.0f}s para não ser bloqueado pelo YouTube...")
            time.sleep(pausa)
        estado["baixou_algum"] = True

        arquivo = baixar(yt_id)
        if not arquivo:
            print("   ⚠️ Falha ao baixar! Vídeo bloqueado ou inexistente.")
            resumo.append(("❌", titulo, "Falha ao baixar"))
            continue

        novo_id = None
        try:
            ext = arquivo.rsplit(".", 1)[-1].lower()
            print("   ⏳ Subindo o Vídeo pro Drive...")
            meta = {"name": f"{artista_yt} - {titulo_limpo} - {yt_id}.{ext}", "parents": [PASTA_DRIVE_ID]}
            media = MediaFileUpload(arquivo, mimetype=MIMETYPES.get(ext, "video/mp4"), resumable=True)
            # num_retries: o Drive às vezes responde 502/503 e a próxima tentativa funciona
            novo_id = drive.files().create(body=meta, media_body=media, fields="id",
                                           supportsAllDrives=True).execute(num_retries=5)["id"]

            print("   💾 Cadastrando no Banco de Dados...")
            dados_post = {"titulo": titulo_limpo, "artista": artista_yt, "youtube_id": yt_id, "drive_id": novo_id}
            cadastrar(dados_post, yt_id)
            print("   ✅ Concluído com Sucesso!")
            resumo.append(("✅", titulo_limpo, artista_yt))
        except Exception as err:
            print(f"   ❌ Erro durante o processo: {err}")
            resumo.append(("❌", titulo, f"Erro: {err}"))
            # Se o cadastro falhou, apaga o vídeo do Drive para não ficar órfão/duplicado na próxima tentativa
            if novo_id:
                try:
                    drive.files().delete(fileId=novo_id, supportsAllDrives=True).execute()
                except Exception:
                    pass
        finally:
            if os.path.exists(arquivo):
                os.remove(arquivo)


def escrever_relatorio():
    caminho = os.environ.get("GITHUB_STEP_SUMMARY")
    if not caminho:
        return
    with open(caminho, "a", encoding="utf-8") as f:
        f.write("## Resultado\n\n| | Música | Detalhe |\n|---|---|---|\n")
        for status, titulo, detalhe in resumo:
            f.write(f"| {status} | {str(titulo).replace('|', '/')} | {str(detalhe).replace('|', '/')} |\n")


def main():
    # Cada linha pode trazer o artista depois de "|": "https://youtu.be/... | Bon Jovi"
    links = []
    for linha in os.environ.get("LINKS", "").splitlines():
        urls = re.findall(r"https?://[^\s|]+", linha)
        artista = linha.split("|", 1)[1].strip() if len(urls) == 1 and "|" in linha else ""
        links += [(u, artista) for u in urls]
    if not links:
        sys.exit("Nenhum link recebido.")

    print("🔑 Conectando ao seu Google Drive...")
    drive = conectar_drive()
    print("✅ Conectado com sucesso!")
    if not COOKIES:
        print("ℹ️ Sem cookies do YouTube configurados (secret YT_COOKIES).")

    estado = {"baixou_algum": False}
    for link, artista in links:
        processar_link(link, artista.strip() or None, drive, estado)

    escrever_relatorio()
    ok = sum(1 for s, *_ in resumo if s == "✅")
    falhas = sum(1 for s, *_ in resumo if s == "❌")
    print(f"\n🎉 FIM! {ok} cadastrada(s), {falhas} falha(s).")
    # Marca a execução como falha no app se algo deu errado, para você ir ver o log
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
