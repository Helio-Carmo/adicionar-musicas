# Descobre o artista e o nome limpo da música a partir do título do vídeo do YouTube.
# Ex.: "Mama, I'm Coming Home - Ozzy Osbourne | Karaoke Version | KaraFun"
#   -> artista "Ozzy Osbourne", música "Mama, I'm Coming Home"

import re
import string
import time
import unicodedata
import requests

# Palavras de vídeo de karaokê que não fazem parte do nome da música
_LIXO = [
    r"karaok[eêé]s?", r"videok[eê]", r"version", r"vers[aã]o", r"instrumental", r"lyrics?", r"letras?", r"playback",
    r"melody", r"hd", r"cc", r"with backing vocals", r"w/ ?b\.?v", r"originally performed by", r"as popularized by",
    r"in the style of", r"made famous by", r"original key", r"original", r"audio", r"with lyrics", r"no vocals?",
    r"com letras?", r"com letras? rolantes?", r"sem vocal", r"letras? rolantes?", r"f[aá]cil de cantar", r"arranjo exclusivo", r"no guide melody",
    r"guide melody", r"bvs?", r"with lyrics on screen", r"lyrics on screen", r"on screen", r"karaoke songs with lyrics",
    r"karaoke songs", r"no lead vocal", r"karaoke video",
]
# Expressões longas primeiro, para "Letra Rolante" sair inteira e não sobrar "Rolante"
LIXO = "|".join(sorted(_LIXO, key=len, reverse=True))
SEPARADORES = r"\s+[-–—|•}]\s+|\||\s+-\s*|\s*-\s+"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def norm_artista(s):
    # "Felipe & Rodrigo" == "Felipe e Rodrigo" == "Felipe and Rodrigo"
    return " ".join(w for w in norm(s).split() if w not in ("e", "and", "y", "the"))


def _comeca_com_artista(trecho, artista):
    return (norm_artista(trecho) + " ").startswith(norm_artista(artista) + " ")


def _limpar_busca(texto, canal):
    if canal:
        texto = re.sub(re.escape(canal), " ", texto, flags=re.I)
    texto = re.sub(r"[#@]\w+", " ", texto)  # hashtags e @canal
    texto = re.sub(rf"(?i)\b({LIXO})\b", " ", texto)
    texto = re.sub(r"[^\w\s'&]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _contem(texto_norm, trecho):
    # Compara ignorando "e"/"&"/"and": "Chitãozinho & Xororó" aparece em "Evidências - Chitãozinho e Xororó"
    t = norm_artista(trecho)
    texto = " ".join(w for w in texto_norm.split() if w not in ("e", "and", "y", "the"))
    return bool(t) and f" {t} " in f" {texto} "


def _buscar_deezer(q, tipo="search"):
    for tentativa in range(5):
        try:
            j = requests.get(f"https://api.deezer.com/{tipo}", params={"q": q, "limit": 5}, timeout=15).json()
        except Exception:
            j = {"error": True}
        if "error" not in j:
            return j.get("data", [])
        time.sleep(2 + 2 * tentativa)  # limite de consultas do Deezer: espera e tenta de novo
    return None


def identificar(titulo, canal=None):
    """Procura no Deezer. Retorna (artista, musica); cada um pode ser None se não houver certeza."""
    trechos = [_limpar_busca(p, canal) for p in re.split(SEPARADORES, titulo or "")]
    trechos = [p for p in trechos if p]
    nt = norm(titulo)
    artista_fraco = None
    for q in dict.fromkeys([_limpar_busca(titulo or "", canal), " ".join(trechos[:2])]):
        if not q:
            continue
        dados = _buscar_deezer(q)
        if dados is None:
            break
        for faixa in dados:
            nome, musica = faixa["artist"]["name"], faixa["title_short"]
            if not _contem(nt, nome):
                continue
            # Música inteira presente no título: confiamos no artista e no nome oficial da música
            if _contem(nt, musica):
                return nome, musica
            # O nome do artista aparece no título: o artista é confiável mesmo se a música veio com outra grafia
            artista_fraco = artista_fraco or nome
    if artista_fraco:
        return artista_fraco, None
    # Última tentativa: algum trecho do título é exatamente o nome de um artista ("... - Whitesnake | ...")
    # (o 1º trecho costuma ser a música; e não usamos trechos de onde o nome do canal foi tirado)
    brutos = [_limpar_busca(p, None) for p in re.split(SEPARADORES, titulo or "")]
    brutos = [p for p in brutos if p]
    for trecho in brutos[1:4]:
        if canal and norm(canal) in norm(trecho):
            continue
        for a in _buscar_deezer(trecho, "search/artist") or []:
            if norm_artista(a["name"]) == norm_artista(trecho):
                return a["name"], None
    return None, None


def _capitalizar(s):
    # "IT'S MY LIFE" -> "It's My Life"; não mexe em títulos com maiúsculas/minúsculas normais
    letras = [c for c in s if c.isalpha()]
    if len(letras) > 3 and all(c.isupper() for c in letras):
        return string.capwords(s.lower())
    return s


def limpar_titulo(titulo, artista=None, canal=None):
    """Tira 'Karaoke', nome do canal, nome do artista, emojis etc. e deixa só o nome da música."""
    t = titulo or ""
    # Remove (Karaoke Version), [KARAOKÊ], 【No Guide Melody】 ... mas mantém (Não) Quero, (Ao Vivo) etc.
    t = re.sub(rf"(?i)[\(\[\{{【][^\(\)\[\]\{{\}}【】]*\b({LIXO})\b[^\(\)\[\]\{{\}}【】]*[\)\]\}}】]", " ", t)
    t = re.sub(r"[\U0001F000-\U0001FFFF☀-➿⭐♪-♯]", " ", t)  # emojis 🎤 ⭐ ♬
    t = re.sub(r"[#@]\w+", " ", t)  # hashtags e @canal
    partes = []
    trechos = re.split(SEPARADORES, t)
    for p in trechos:
        p = re.sub(r"(?i)\b(originally performed by|as popularized by|in the style of|made famous by)\b.*", " ", p)
        p = re.sub(rf"(?i)\b({LIXO})\b", " ", p)
        if canal and norm(canal) and f" {norm(canal)} " in f" {norm(p)} ":
            # Trecho com o nome do canal são créditos ("Grupo Menos é Mais e Pablo"), não o nome da música
            if len(trechos) > 1:
                continue
            p = re.sub(re.escape(canal), " ", p, flags=re.I)
        p = re.sub(r"\(\s*\)|\[\s*\]", " ", p)
        p = re.sub(r"\s+", " ", p).strip(" .,:;/\\\"'*~_-")
        # Parêntese sobrando numa ponta: "música (" ou ") música"
        if p.count("(") > p.count(")"):
            p = p.rstrip(" (") if p.rstrip().endswith("(") else p + ")"
        p = p.lstrip(")").strip()
        if p:
            partes.append(p)
    # Tira os trechos que são o artista ("Bon Jovi", "Carol Biazin, Léo Foguete", "Matheus & Kauan (part. X)")
    if artista and len(partes) > 1:
        sem_artista = [p for p in partes if not _comeca_com_artista(p, artista)]
        partes = sem_artista or partes
    if not partes:
        return _capitalizar(re.sub(r"\s+", " ", titulo or "").strip())
    # Quando sobra "Artista Música" no mesmo trecho, tira o artista do começo
    musica = partes[0]
    if artista and _comeca_com_artista(musica, artista) and norm_artista(musica) != norm_artista(artista):
        n = len(norm_artista(artista).split())
        palavras = musica.split()
        # tira do começo as palavras do artista (ignorando "e", "&")
        while n and palavras:
            if norm_artista(palavras[0]):
                n -= 1
            palavras.pop(0)
        while palavras and not norm_artista(palavras[0]):
            palavras.pop(0)
        musica = " ".join(palavras) or musica
    return _capitalizar(musica)


def artista_e_titulo(titulo, canal=None, artista_fixo=None):
    """Retorna (artista ou None, titulo_limpo)."""
    artista_deezer, musica = identificar(titulo, canal)
    artista = artista_fixo or artista_deezer
    # O nome oficial da música só vale se o Deezer achou o mesmo artista
    if musica and norm(artista_deezer) == norm(artista):
        return artista, musica
    return artista, limpar_titulo(titulo, artista, canal)
