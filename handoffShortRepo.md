# Handoff: Short-Clip-Pipeline für Daggerheart-Sessions

Stand: 18.10.2026
Empfänger: Planungsagent (Claude Opus)
Status: Entwurf auf Basis einer Evaluation. Alle Annahmen zu bestehenden Repos und zum OKF-Bundle sind **ungeprüft**. Bitte zuerst verifizieren.

---

## 0. Auftrag

1. Lies die Git-Repos, deren Pfade der Nutzer dir separat gibt (Transkriptions-Repo, OKF-Knowledge-Bundle, ggf. weitere).
2. Erstelle darauf aufbauend einen **konkreten, umsetzbaren Plan**: Architektur mit Dateipfaden, Phasen, Tasks, Akzeptanzkriterien, Risiken, offene Entscheidungen.
3. Ändere **keinen** bestehenden Code und keine Daten, bevor der Plan freigegeben ist.
4. Führe **keine** Schneide-, Render- oder Upload-Schritte mit echtem Material ohne Freigabe aus.

---

## 1. Ziel

- **Primär:** TikTok-Highlight-Clips aus Pen-&-Paper-Sessions (Daggerheart, Gruppe mit mehreren Spielenden und einer Spielleitung).
- **Format:** 9:16, 1080×1920, H.264/AAC, Länge vorerst 20–45 s (Storytelling bis ca. 60 s).
- **Hook:** Kernaussage oder Reaktion in den ersten 0–3 s, zusätzlich als Text-Overlay.
- **Untertitel:** wortgenau, eingebrannt, 2–4 Wörter pro Einblendung, Sprecherfarben.
- **Autonomie:** Claude übernimmt Auswahl, Schnitt, Untertitel und Caption-Vorschläge.
- **Lernen:** Claude verbessert über Zeit seine Regeln und Beispiele, aber nur nach menschlicher Freigabe.
- **Veröffentlichung:** Der Mensch postet, nicht die Pipeline.
- **Sprache:** Deutsch primär, Englisch sekundär.

---

## 2. Ausgangslage (vom Nutzer berichtet, bitte prüfen)

- Es existiert ein Repo, das **die kompletten Streams transkribiert** und **Sprechern zuordnet**.
- Die Sprecherzuordnung hat ca. **10 % fehlerhafte Trennungen**.
- Der Output fließt in ein **OKF-Knowledge-Bundle**. Das Format ist mir nicht bekannt. Der Planungsagent muss Schema und Inhalt selbst lesen.
- Der **Video-Agent** soll Lesezugriff auf dieses Bundle haben. Der Umfang ist noch offen.
- Alle Repos sind Git-Repos. Der Nutzer gibt die Pfade separat an.

**Hypothese, die du verifizieren sollst:** Das bestehende Repo ist die Source of Truth für Transkripte, Zeitstempel und Sprecher. Es sollte **nicht ersetzt**, sondern über einen Adapter eingebunden werden. Die 10 % Fehler sind das Hauptproblem, das die Pipeline lösen muss.

---

## 3. Constraints

- **Privat und nicht kommerziell** zu Beginn. Eine spätere Monetarisierung darf nicht ausgeschlossen werden. Modelle und Lizenzen daher früh prüfen.
- **Einwilligung aller Mitspielenden** (§ 22 KUG, DSGVO Art. 7) vor jeder Veröffentlichung. Führe ein Register (`consent.yaml` oder gleichwertig) mit Datum, Umfang (Plattformen, KI-Verarbeitung) und Widerruf.
- **Daggerheart-Lizenz (Darrington Press Community Gaming License):** Attribution, Hinweis „Daggerheart™ Compatible“, kein Markenname im Titel, keine offiziellen Artworks oder Logos. Den aktuellen Wortlaut vor Veröffentlichung selbst prüfen.
- **Keine Stimm- oder Gesichtsprofile** ohne vorherige rechtliche Prüfung (DSGVO Art. 9, KI-Verordnung). Das ist eine offene Frage.
- **Freigabe-Gate:** Kein Clip wird ohne menschliche Freigabe exportiert oder hochgeladen.
- **Nur Eigenmaterial:** Keine fremde Musik, keine Twitch-/YouTube-Logos, keine Wasserzeichen.

---

## 4. Evaluation (Websuche, Stand Okt. 2026)

Die Recherche-Funktion war in diesem Gespräch nicht aktiv. Die Ergebnisse stammen aus normalen Websuchen und sind **nicht vollständig** verifiziert.

### 4.1 Diarisierung

| Option | Befund | Bewertung für uns |
|---|---|---|
| PyannoteAI (Cloud) | Bester Wert im ICML-2026-Benchmark mit 11,2 % DER über 5 Modelle, 196,6 h, inkl. Deutsch | Starker Vergleichskandidat, Cloud, kostenpflichtig |
| DiariZen | 13,3 % DER, offen, aber Gewichte nur CC-BY-NC | Nicht für spätere Monetarisierung verwenden |
| NVIDIA Sortformer | Laut NVIDIA für Produktion empfohlen; laut Community-Feedback nur bis 4 Sprecher (v2.1), 8-Sprecher-Version in Arbeit | **Problem:** Tischrunden haben oft 4–6 Personen |
| NeMo-Kaskade (MarbleNet + TitaNet + MSDD) | Alternative in NeMo | Prüfen, falls Sortformer am Sprecherlimit scheitert |
| pyannote community-1 (lokal) | Ursprünglich im Entwurf, offen lizenziert | Aktuelle Basis-Option; im Benchmark gegen Alternativen prüfen |

### 4.2 Transkription

- **NVIDIA Parakeet TDT 0.6B v3:** unterstützt Deutsch und 24 weitere europäische Sprachen, liefert Wort-Zeitstempel, läuft lokal auf GPU. v2 ist nur Englisch.
- **WhisperX large-v3** (Entwurf): bleibt Vergleichsbaseline.
- **Cloud (Deepgram Nova-3, AssemblyAI Universal-3.5 Pro, Speechmatics, ElevenLabs Scribe):** Herstellerangaben zu Diarisierung und cpWER sind nicht unabhängig. Nur auf eigenem Material vergleichen.
- **Wichtig:** Das Transkript ist bereits vorhanden. Die Frage ist daher nicht die Transkription, sondern die **Sprecherzuordnung und Fehlerkorrektur** (ca. 10 %).

### 4.3 Fehlerkorrektur bei Sprecherzuordnung (nicht im Entwurf enthalten)

- LLM-basierte Korrektur über Kontext, Rollennamen und Gesprächsfluss.
- Stimmprofil-Embeddings pro Spielender, nur nach Prüfung von Punkt 3.
- Einzelspuren (OBS Multitrack): reduziert das Problem am stärksten. Der Nutzer soll klären, ob das Setup das zulässt.
- Metriken: DER und cpWER gegen eine manuell korrigierte Referenz (ca. 15–20 min).

### 4.4 Clipping-Tools (fertige Produkte)

- Vertreter: OpusClip, Vizard, Submagic, Descript, CapCut (Upload bis 3 h / 10 GB), Kapwing, Videotto.
- Sie sind schnell nutzbar, lernen aber nicht aus eigenen Daten, senden Material in die Cloud und sind für Rollenspiel-Gespräche nicht getestet.
- **Rolle:** Vergleichsbaseline. Kein Kernbaustein.

### 4.5 Schnitt und Rendering

- **mcp-video** (Open Source, PyPI): ca. 91 Tools auf Basis von FFmpeg, u. a. Untertitel, Resize auf 9:16, Transkription, Qualitätsprüfung. Installierbar per `uvx` oder `pip`. Prüfen: Code, Wartungsstand, Lizenz, ob es die eigene Skriptbasis ersetzt oder ergänzt.
- **Community-FFmpeg-MCP-Server:** viele dünne Wrapper, teils unklare Wartung. Vor Nutzung auditieren, nicht blind einbinden.
- **FFmpeg direkt in eigenen Skripten** mit ASS-Untertiteln bleibt die robusteste Option.
- **Remotion:** nur für animierte Overlays sinnvoll. Lizenz für Firmen ab 4 Personen kostenpflichtig.

### 4.6 Claude-Ökosystem

- Skills unter `.claude/skills/<name>/SKILL.md`, Skripte per Bash.
- Desktop-Scheduled-Tasks laufen nur lokal, wenn Desktop-App und Rechner aktiv sind.
- Cloud-Routines sind für GPU-Arbeit und große Dateien ungeeignet.
- Agent SDK nur, falls die Pipeline ohne Claude-Code-Oberfläche laufen soll.

---

## 5. Vorgeschlagene Architektur (Hypothese, bitte validieren)

```
[Bestehendes Transkriptions-Repo]  →  Adapter  →  [Clip-Studio]
   (Source of Truth: Text, Zeit,              │
    Sprecher, ~10 % Fehler)                   ├─ Kandidaten (Signale + Claude-Bewertung)
                                              ├─ Sprecher-Korrektur (LLM + ggf. Einzelspur)
[OKF-Bundle]  ── read-only ──────────────────►├─ Schnitt + Untertitel (FFmpeg/ASS)
   (Kontext für Video-Agent)                  ├─ QA (Frames, Consent-Check, Safe Zones)
                                              ├─ Freigabe-Gate (Mensch)
                                              └─ Decision-Log + rules.md + examples/
```

**Phasen (Vorschlag):**

1. **Ist-Analyse:** bestehendes Repo, OKF-Schema, Output-Format, Sprecher-Fehlerbilder. Ergebnis: kurzes Dokument mit Befunden.
2. **Benchmark-Protokoll:** Referenzsegment (15–20 min) manuell gelabelt. Vergleich: bestehende Pipeline vs. Parakeet v3 + Diarisierung vs. pyannote-Cloud. Metriken DER und cpWER. Entscheidung treffen.
3. **Adapter** vom bestehenden Repo zu einem einheitlichen Segment-Format (JSON mit Wort-Zeitstempeln und Sprecher-ID).
4. **Kandidaten-Auswahl:** Signale (Lautstärke, Lachen, Würfel-Keywords) und Claude-Bewertung nach `rules.md`.
5. **Render:** FFmpeg-Skripte, ASS-Untertitel, 9:16-Layout, Lautheitsnormalisierung.
6. **QA und Freigabe-Gate.**
7. **Lern-Loop:** Entscheidungen in SQLite, Beispiele in `examples/`, Regeländerungen nur als Diff zur Freigabe.

---

## 6. Offene Entscheidungen (für den Nutzer, Antworten einholen)

1. Maximale Sprecherzahl pro Session (Sortformer-Limit)?
2. Gibt es OBS-Multitrack oder Discord-Einzelspuren?
3. Lokale NVIDIA-GPU mit mindestens 8 GB VRAM vorhanden?
4. Sind Einwilligungen eingeholt? Wer hat sie erteilt?
5. Ist Monetarisierung geplant? (Beeinflusst Lizenzwahl.)
6. Format und Zugriffsrechte des OKF-Bundles. Darf der Video-Agent es schreiben oder nur lesen?
7. Welche Clip-Formate sollen zuerst entstehen?

---

## 7. Lieferobjekte des Planungsagenten

- Ist-Analyse (Repos, OKF-Bundle, Schemas, Fehlerbilder), mit Dateipfaden.
- Architekturentwurf mit konkreter Dateistruktur.
- Phasenplan mit Tasks und Akzeptanzkriterien pro Phase.
- Benchmark-Protokoll inklusive Referenzdatensatz-Definition.
- Risikoliste (Lizenz, Datenschutz, Sprecherfehler, Lerneffekt vs. Rauschen).
- Konkrete Tasks für Woche 1–2.
- Liste offener Punkte aus Abschnitt 6, ergänzt um eigene Fragen.

---

## 8. Nicht-Ziele

- Keine automatische Veröffentlichung auf TikTok.
- Keine Gesichts- oder Stimmerkennung über Einzelpersonen ohne Rechtsprüfung.
- Keine fremde Musik aus Streams.
- Keine automatische Änderung von `rules.md` ohne menschliche Freigabe.
- Kein Neuschreiben des bestehenden Transkriptions-Repos ohne Plan.

---

## 9. Quellen der Evaluation (Auswahl)

- ICML 2026, „Benchmarking Diarization Models“ (icml.cc/virtual/2026/77326)
- NVIDIA NGC, Parakeet-Collections (catalog.ngc.nvidia.com)
- NVIDIA, Sortformer-FAQ (perspectives.nvidia.com)
- Hedy-Feature-Request zu Parakeet und Sortformer-Sprecherlimit (feedback.hedy.bot)
- Kili Technology, „Speaker Diarization Models Guide“ (DiariZen-Lizenz)
- mcp-video, PyPI (pypi.org/project/mcp-video/)
- Vendor-Vergleichsseiten zu Clipping-Tools (schwache Quellen, nur als Orientierung)

Bitte alle Zahlen vor Verwendung in Entscheidungen gegenprüfen.
