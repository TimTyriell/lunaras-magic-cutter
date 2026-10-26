---
name: calibrate-layout
description: Set facecam crop boxes for a team's stream layout in config/layouts.toml so rendered clips cut to the active speaker. Use when the user says /calibrate-layout <team>, or when clips render only wide shots.
---

# /calibrate-layout <team>   (team-a | team-b)

Needs one fetched clip of that team (`work/<stem>/clips/<id>/src.mp4`). If none, run `/cut-clip` steps 1 only for any candidate.

1. Source size: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 <src.mp4>`.
2. Extract 3 frames at different times: `ffmpeg -v error -y -ss <t> -i <src.mp4> -frames:v 1 work/layout_<team>_<n>.png`.
3. Read the images. Identify each facecam tile. Map tiles to person keys using on-screen name labels if present; otherwise ask the user which tile is whom (show tile positions). Never guess identities from faces.
4. Per person propose `[x, y, w, h]` in source pixels covering the whole cam tile incl. frame and name plate (render fits it to 1080 wide on a blurred fill; no 9:16 crop needed).
5. Verify: crop each box (`ffmpeg ... -vf crop=w:h:x:y -frames:v 1 work/layout_<team>_<person>.png`) and Read them. Adjust until each shows exactly one cam.
6. Show the table to the user; on confirmation write the `[<team>]` section in `config/layouts.toml`.

Layout varies by season? Add a dated section and note it in the file comment (ponytail: render.py reads only `[<team>]` until that is needed).
