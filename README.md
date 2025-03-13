# Discord Music Bot

Bot muzyczny Discord z zaawansowanymi funkcjami odtwarzania i zarządzania muzyką z YouTube.

## Funkcje

- Odtwarzanie muzyki z YouTube (pojedyncze utwory i playlisty)
- Wyszukiwanie utworów na YouTube
- Zarządzanie kolejką odtwarzania
- Pauza/wznawianie utworów
- Pomijanie utworów
- Regulacja głośności
- Wyświetlanie tekstów piosenek
- Zapisywanie i wczytywanie playlist
- Zapętlanie utworów
- Czyszczenie wiadomości
- Rzut kośćmi

## Wymagania

- Python 3.7+
- FFmpeg
- [Token Discord Bot](https://discord.com/developers/applications)
- [Token Genius API](https://genius.com/api-clients) (opcjonalnie, do tekstów piosenek)

## Instalacja

1. Sklonuj repozytorium:
```
git clone https://github.com/Kazmir_BO/Discord-music-bot.git
cd Discord-music-bot
```

2. Zainstaluj wymagane pakiety:
```
pip install -r requirements.txt
```

3. Zainstaluj FFmpeg:
   - Windows: [Pobierz FFmpeg](https://ffmpeg.org/download.html) i dodaj do zmiennej PATH
   - Linux: `sudo apt install ffmpeg`
   - MacOS: `brew install ffmpeg`

4. Utwórz plik `.env` w głównym katalogu projektu i dodaj swój token Discord:
```
TOKEN=twój_token_discord_bot
GENIUS_TOKEN=twój_token_genius_api
```

## Uruchomienie

```
python MainBot.py
```

## Komendy

| Komenda | Aliasy | Opis |
|---------|--------|------|
| +help | +h, +man | Wyświetla pomoc |
| +play <url/tytuł> | +p | Odtwarza utwór z podanego URL lub wyszukuje podany tytuł |
| +find <tytuł> | +f | Wyszukuje 5 utworów pasujących do tytułu |
| +pause/resume | +pr | Wstrzymuje/wznawia odtwarzanie |
| +skip [numer] | +sk | Pomija bieżący utwór lub przechodzi do określonego utworu w kolejce |
| +queue | +q | Wyświetla kolejkę odtwarzania |
| +delete <numer> | +dl | Usuwa utwór o podanym numerze z kolejki |
| +stop | +s | Zatrzymuje odtwarzanie i czyści kolejkę |
| +disconnect | +d | Rozłącza bota z kanału głosowego |
| +volume [procent] | +v | Wyświetla lub ustawia głośność (0-200%) |
| +lyrics | +l | Wyświetla tekst aktualnie odtwarzanego utworu |
| +loop | +lp | Włącza/wyłącza zapętlanie aktualnego utworu |
| +saveplaylist <nazwa> | +sp | Zapisuje aktualną kolejkę jako playlistę |
| +loadplaylist <nazwa> | +loadp | Wczytuje zapisaną playlistę |
| +playlists | +pl | Wyświetla listę dostępnych playlist |
| +roll <ilość> <rodzaj> | +r | Wykonuje rzut kośćmi |
| +clear <ilość> | +c | Usuwa określoną liczbę wiadomości |

## Struktura projektu

```
Discord-music-bot/
├── MainBot.py             # Główny plik bota
├── cogs/                  # Moduły bota
│   ├── AdminCog.py        # Komendy administracyjne
│   ├── FunCog.py          # Komendy rozrywkowe
│   └── MusicCog.py        # Komendy muzyczne
├── playlists/             # Zapisane playlisty
├── files/                 # Pliki tymczasowe
├── logs/                  # Logi błędów
├── requirements.txt       # Wymagane pakiety
└── .env                   # Zmienne środowiskowe
```

## Licencja

Ten projekt jest dostępny na licencji MIT - zobacz plik [LICENSE](LICENSE) dla szczegółów.
