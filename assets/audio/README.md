# Audio sources

## `orbit_synthwave.mp3`

Soundtrack of the Orbit Atlas film (`examples/orbit_atlas.py`, `docs/assets/home/orbit-film.mp4`).

- **Title:** Synthwave House Loop
- **Author:** Fupi
- **License:** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), as listed on the source page (checked 2026-11-01)
- **Source page:** <https://opengameart.org/content/synthwave-house-loop>
- **Source file:** <https://opengameart.org/sites/default/files/synthwavehouse.wav>
  (SHA-256 `5d3bacaf3c1807540665c01735e44126da485d0e4800c168227ebf5a7892e230`, 50.5 seconds, 114 BPM)
- **Changes:** sped up from 114 to 128 BPM without a pitch change, so the music fits the film's beat cuts; cut to the first 17.5 seconds; encoded as 192 kbps MP3.

```bash
ffmpeg -i synthwavehouse.wav -af "atempo=128/114" -t 17.5 \
  -c:a libmp3lame -b:a 192k orbit_synthwave.mp3
```
