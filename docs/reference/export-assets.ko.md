---
description: quickthumb의 샘플, 에셋, 재현성에 관한 레퍼런스입니다.
---

# 샘플, 에셋, 재현성 { #samples-assets-and-reproducibility }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## 기준 샘플 { #canonical-samples }

`sample()`은 내보내기 결과를 비교할 때 사용하는 렌더러 독립적인 기준을 JSON으로 직렬화할 수 있는 `FrameSequence`로 반환합니다. Canvas와 Deck은 같은 계약을 따르며, 캔버스를 관찰한 결과는 그 캔버스만 담은 한 장짜리 덱의 결과와 같습니다.

```python
still = canvas.sample()                         # settled frame(s), as PNG/PDF/PPTX draw them
timed = deck.sample(fps=10)                     # uniform grid over the whole animated timeline
probe = deck.sample([0.0, 1.25, 4.0], hold=2.0) # explicit instants, ascending
```

- **프레임.** 각 `CanonicalFrame`은 `width * height`개의 픽셀을 원시 8비트 RGBA로 보관합니다. 픽셀은 왼쪽 위부터 행 우선 순서이며 sRGB와 비연관 알파(straight alpha)를 사용합니다. 바이트는 `data`에 base64로 인코딩되고, 해당 바이트의 `sha256`도 포함됩니다. `index`는 시퀀스에서 프레임의 위치, `slide`는 표시되는 페이지입니다. 다이제스트나 크기가 데이터와 일치하지 않는 프레임은 불러올 때 거부됩니다.
- **정지 화면 캡처**(`capture="still"`)는 슬라이드 순서대로 페이지마다 한 프레임을 담습니다. 각 페이지의 원래 크기와 투명도를 유지합니다. `time`은 `None`, `duration`은 `0`이며 `timeline`은 비어 있습니다.
- **타임라인 캡처**(`capture="timeline"`)는 애니메이션 WebM/MP4 내보내기가 재생하는 타임라인을 관찰합니다. 전환, Morph, 레이어 애니메이션, 내레이션에 따른 슬라이드 길이, 명시적인 길이가 없는 페이지에서 안정된 화면을 `hold`초(기본 3초) 유지하는 구간이 포함됩니다. 프레임은 초 단위 `time`의 오름차순으로 정렬되며 첫 슬라이드의 크기를 공유합니다. 불투명한 `matte`(기본 검정)에 합성되고 이 색상은 `#RRGGBB`로 보고됩니다. 현재 덱 GIF 내보내기는 명시적인 슬라이드 길이와 내레이션 길이를 무시하므로, 그런 길이가 없는 덱에서만 이 타임라인과 일치합니다.
- **샘플링.** `fps=N`(최대 120)은 `duration` 이전의 모든 `k / N` 시점을 관찰합니다. 직접 지정하는 시점은 오름차순이어야 하며, `duration` 이상인 시점은 마지막으로 안정된 프레임을 보여 줍니다. 한 캡처는 최대 100,000개 시점을 관찰합니다. 직접 지정한 목록이나 fps 격자가 이보다 크면 프레임을 렌더링하기 전에 `ValidationError`로 거부됩니다. 이 격자는 관찰 일정이며 내보내기의 프레임 일정은 아닙니다. 각 내보내기는 구간마다 자체 프레임 격자를 사용하고, 한 프레임보다 짧은 슬라이드는 한 프레임 길이로 늘립니다.
- **타이밍.** `duration`은 정확한 타임라인 길이이며 `fps`나 요청한 시점에 영향을 받지 않습니다. 각 `TimelineSegment`는 슬라이드의 절대 `start`, `transition_end`, `animation_end`, `end`를 나노초 단위로 반올림해 제공합니다. 슬라이드는 `[start, end)` 동안 화면에 있으므로 경계 시점은 새로 들어오는 슬라이드에 속합니다.
- **메모리.** 서로 다른 프레임의 원시 RGBA가 768 MiB를 넘는 캡처는 `ValidationError`로 거부됩니다. 정지 캡처의 모든 페이지 또는 타임라인 캡처의 한 프레임만으로 한도를 넘으면 어떤 프레임도 렌더링하기 전에 거부합니다. 시점 수나 `fps`, `hold`를 줄이거나 문서를 작게 만드세요.
- **환경.** `sample()`과 `export()`는 quickthumb, Pillow, FreeType 버전, 텍스트 레이아웃 엔진(`basic` 또는 `raqm`), 사용 가능한 RAQM/HarfBuzz/FriBidi 버전을 보고합니다. 비디오 레이어가 있는 문서에는 FFmpeg 버전도 포함됩니다. 동작하는 FFmpeg 없이 비디오를 샘플링하면 프레임을 렌더링하기 전에 `RenderingError`가 발생합니다. `environment.fonts`는 해당 작업에서 실제로 선택한 글꼴 페이스의 바이트를 보고하며, 에셋 매니페스트는 작성된 참조를 별도로 설명합니다.

## 렌더링 재현성 { #render-reproducibility }

글꼴 패밀리 이름과 `QUICKTHUMB_DEFAULT_FONT`는 컴퓨터의 글꼴 검색 경로에 따라 달라집니다. 이름을 이식 가능한 식별자로 취급하지 말고 선택된 페이스를 확인하세요.

```python
capture = canvas.sample()
for font in capture.environment.fonts:
    print(font.source, font.sha256, font.variations)
```

각 페이스에는 확인된 파일 경로(또는 `pillow:default`), SHA-256, 글꼴 축 이름을 키로 하는 적용된 가변 좌표가 있습니다. 해시는 글꼴 바이트를 식별합니다. Pillow 내장 페이스의 바이트를 사용할 수 없으면 해시를 보고하지 않습니다. 경로는 진단용입니다. 컴퓨터 간에는 해시와 좌표를 비교하세요. 현재 작업에서 불러온 페이스만 보고되며, 사용하지 않은 이름 지정 글꼴과 이전 작업의 페이스는 제외됩니다.

원격 글꼴과 Google 글꼴은 확인된 바이트의 콘텐츠 주소 기반 사본에서 불러옵니다. 따라서 다른 문서가 원래 URL을 새로 고쳐도 미리 가져온 페이스가 바뀌지 않습니다. 사본은 에셋 캐시에 저장되며 호출자가 관리하는 정리 수명 주기를 따릅니다. 작업 중에는 로컬 입력 파일을 변경하지 마세요.

기준 래스터 출력을 반복해서 얻으려면 동일한 문서 데이터, 입력 에셋 바이트, 선택된 글꼴과 가변 좌표, 렌더링 옵션, 환경을 사용하세요. 지원되는 절차적 효과에는 시드를 지정하세요. 글꼴, 셰이핑, 래스터라이저 버전이 다르면 레이아웃과 가장자리 픽셀이 달라질 수 있습니다. 이 보고서는 이러한 입력을 설명하며, 플랫폼이나 네이티브 출력 뷰어 간에 픽셀이 정확히 같다고 보장하지 않습니다. 이런 출력은 형식에 맞는 충실도 허용 오차로 비교하세요.

## 원격 에셋과 캐시 { #remote-assets-and-caching }

`render()`와 `export()`는 원격 이미지, SVG, 텍스트 채우기, 글꼴을 공유 캐시에 내려받으며, `export()`는 사용한 모든 에셋을 설명하는 `asset_manifest`를 반환합니다. 선택 사항인 `prefetch_assets()`는 같은 다운로드를 미리 수행하고 렌더링 없이 매니페스트를 반환합니다. 긴 내보내기 전에 네트워크 오류나 오래된 항목을 발견하거나 오프라인 렌더링을 위해 캐시를 준비할 수 있습니다. 각 `AssetManifestEntry`에는 작성된 그대로의 `source`, 의미에 따른 `asset_type`, `status`, 사용 가능한 식별 정보가 담깁니다. 식별 정보는 `source_key`(정규화된 URL), `cache_key`, `cache_path`, `content_hash`(사용한 바이트의 SHA-256), `fetched_at`(다운로드한 UTC 시각)입니다.

| `status` | 의미 |
| --- | --- |
| `local` | 존재하는 로컬 파일입니다. |
| `missing` | 존재하지 않는 로컬 경로입니다. |
| `network` | 지금 다운로드해 캐시에 기록했습니다. |
| `fresh` | `max_age` 이내인 캐시 항목에서 읽었습니다. `max_age`가 없으면 항상 해당합니다. |
| `stale` | 새로 고칠 수 없어 만료된 캐시 항목에서 읽었거나 오프라인으로 읽었습니다. `stale_reason`이 이유를 설명합니다. |
| `unresolved` | 아직 확인되지 않은 원격 참조입니다. |

환경 변수로 캐시를 제어합니다.

- `QUICKTHUMB_ASSET_CACHE_DIR`: 캐시 디렉터리입니다. 기본값은 시스템 임시 디렉터리입니다.
- `QUICKTHUMB_ASSET_MAX_AGE`: 캐시 항목을 네트워크에서 새로 고치기까지의 초 단위 시간입니다. 새로 고침에 실패하면 기존 바이트를 사용하고 `stale`로 보고합니다. 설정하지 않으면 캐시 항목은 만료되지 않습니다.
- `QUICKTHUMB_ASSET_OFFLINE=1`: 네트워크 요청을 하지 않습니다. 캐시 항목을 사용하며 만료된 항목은 `stale`로 보고합니다.

## 소유권과 재사용 { #ownership-and-reuse }

같은 `Canvas` 또는 `Deck`을 유지하면 `prefetch_assets()`, `sample()`, 내보내기에서 확인 결과를 재사용할 수 있습니다. 각 캔버스는 처음 확인한 원격 결과와 상태를 보관하고, 덱은 슬라이드의 결과를 사용합니다. 원격 이미지, 텍스트 채우기, SVG는 보관된 바이트로 렌더링합니다. Google 글꼴을 포함한 원격 글꼴은 확인된 바이트의 콘텐츠 주소 기반 사본에서 불러오므로, 다른 문서의 URL 새로 고침이 미리 가져온 페이스를 바꾸지 않습니다. 샘플링과 내보내기가 끝날 때까지 캐시 파일을 유지하세요. 현재 캐시 정책으로 같은 참조를 다시 확인하려면 새 문서를 만드세요.

`PrefetchResult`와 `asset_manifest`는 JSON으로 안전하게 표현할 수 있는 보고서이며 리소스 핸들이 아닙니다. JSON을 저장하거나 불러와도 바이트를 전달하거나 다른 문서에 미리 불러오지 않습니다. 새 문서는 유지된 캐시를 재사용할 수 있으며 항목을 사용할 수 있으면 `fresh`로 보고합니다. 로컬 이미지, 글꼴, 비디오, 오디오 경로의 파일은 호출자가 소유합니다. 샘플링이나 내보내기가 끝날 때까지 사용 가능하고 변경되지 않은 상태로 유지하세요. 미리 가져오기는 이런 파일을 고정하거나 복사하지 않습니다. 비디오와 오디오 소스는 미리 가져오기로 다운로드하지 않습니다. 원격 비디오는 필요할 때 FFmpeg가 읽으며 이 캐시 계약에 포함되지 않습니다. 파일/URL 참조가 없는 생성 콘텐츠에는 외부 에셋 항목이 없습니다.

캐시 디렉터리와 정리는 호출자가 관리합니다. Quickthumb은 원격 캐시 파일과 메타데이터를 원자적으로 기록하지만 자동으로 제거하지 않습니다. 문서와 내보내기 워커가 해당 캐시를 더 이상 사용하지 않을 때만 사용하지 않는 항목을 지우세요. 기존 매니페스트는 관찰 결과이며 `cache_path`가 여전히 존재한다는 보장이 아닙니다. 메모리에 보관된 원격 결과를 위해 문서를 명시적으로 닫을 필요는 없습니다. 문서와 함께 해제됩니다.

사용 가능한 캐시 항목도 네트워크 응답도 없으면 소스, 원인, 검색한 캐시 디렉터리를 명시하는 `RenderingError`가 발생합니다. 오래된 입력을 거부하려면 렌더링 전에 매니페스트를 확인하세요.

```python
prefetched = canvas.prefetch_assets()
stale = [entry for entry in prefetched.asset_manifest if entry.status == "stale"]
if stale:
    raise SystemExit(f"stale assets: {[(e.source, e.stale_reason) for e in stale]}")
```

## 에셋과 플러그인 수명 주기 픽스처 { #asset-and-plugin-lifecycle-fixtures }

`tests/test_asset_cache.py`의 공유 글꼴/텍스처 시나리오는 전용 플러그인 레지스트리, 저장소의 TTF, 임시 localhost HTTP 서버가 제공하는 생성 이미지 바이트를 사용합니다. 공개 Canvas/Deck 작업과 캐시 환경 설정을 검증합니다. 제어된 표준 시계로 대기하거나 캐시 파일과 메타데이터를 편집하지 않고 만료 시점을 진행합니다. 공개 네트워크 서비스나 플랫폼별 픽셀 스냅샷은 필요하지 않습니다.

| 시나리오 | 관찰 가능한 근거 | 회귀 검사 |
| --- | --- | --- |
| 네트워크 → 새 문서의 유효한 캐시 → 만료 후 새로 고침 | 확인 상태, 가져온 시각, 변경된 콘텐츠 해시, 실제 글꼴 식별 정보, 디코딩한 PNG 픽셀. 원래 문서는 확인한 바이트를 유지합니다. | `test_combined_resources_refresh_only_for_new_expired_documents` (`canvas`, `deck`) |
| 오프라인 상태의 만료된 캐시 | 플러그인 실행이나 출력 전에 두 리소스 모두 소스, 해시, 가져온 시각, 오프라인/max-age 이유와 함께 `stale`을 보고합니다. 계속 진행하면 요청 없이 원래 RGBA/글꼴 바이트를 얻습니다. | `test_combined_offline_stale_evidence_precedes_optional_rendering` (`canvas`, `deck`) |
| 캐시가 없는 오프라인 글꼴 또는 플러그인 텍스처 | 공개 미리 가져오기가 뒤쪽 슬라이드, 소스 URL, 캐시 디렉터리를 식별합니다. 플러그인 텍스처 오류는 레이어/에셋 경로도 식별합니다. 콜백이나 파일 쓰기는 발생하지 않습니다. | `test_combined_cold_offline_failure_identifies_later_slide_resource` (`font`, `texture`) |
| 래스터 및 네이티브 문서 출력에서 미리 가져온 리소스 | Canvas/Deck 래스터 일치, 실제 글꼴 SHA, 에셋 매니페스트, 네이티브 SVG 텍스트, 정확한 플러그인 PNG 대체 출력 | `test_prefetched_font_and_private_plugin_keep_shared_export_evidence` |
| 선언된 플러그인 의존성 누락 | 이스케이프한 JSON Pointer, 레이어 식별 정보, 쓰기 전 실패 | `test_plugin_declared_missing_assets_fail_before_output_or_callback` |
| 플러그인의 네이티브 일치, 허용되는 차이, 불일치 또는 미지원 대상 | 실제 로컬 SVG 비교와 채택된 네이티브/PNG 표현, 설명된 대체 출력과 엄격 모드 거부 | `tests/test_plugin_svg.py`, `tests/test_plugin_runtime.py`의 `test_plugin_document_fallback_reports_and_preserves_output` |
| 기본, 패밀리, 파일, 가변 글꼴 | 샘플/내보내기 환경에서 실제 선택된 페이스 해시와 적용된 좌표 | `tests/test_canonical_sampling.py`의 글꼴 식별 정보 사례 |

위 예제처럼 반환된 매니페스트로 오래된 입력을 거부할지는 호출자가 결정합니다. 오래된 입력을 자동 거부하는 내보내기 플래그는 없습니다. 오프라인 픽스처는 플러그인 콜백이나 대상 변경 전에 근거를 사용할 수 있는지 확인하고, 그 뒤 호출자가 오래된 바이트로 렌더링하기로 선택한 결과를 별도로 검증합니다. 캐시가 없는 경우 글꼴이나 빈 플러그인 텍스처로 대체하지 않고 실패합니다.

`uv run --locked pytest tests/test_asset_cache.py tests/test_plugin_runtime.py
tests/test_plugin_svg.py tests/test_canonical_sampling.py --no-cov -q`를 실행하세요.
이 파일들은 기존 자동화 `pytest tests/` 품질 작업에 포함됩니다. 시나리오 이름과 매개변수 ID가 리소스/문서 실패를 식별합니다. 예상 해시는 제어된 소스 바이트로 계산하고, 렌더링한 샘플은 기록된 동일 글꼴/렌더링 환경에서 비교합니다. 컴퓨터나 네이티브 뷰어 간에 글꼴 픽셀이 같다고 보장하지는 않습니다.
