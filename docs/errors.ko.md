---
description: 안정적인 코드와 JSON Pointer 위치를 사용하는 공통 구조화 오류 계약으로 quickthumb의 검증, 에셋 누락, 내보내기, CLI 실패를 처리합니다.
---

# 구조화된 오류 { #structured-errors }

잘못된 필드나 누락된 에셋, 지원하지 않는 내보내기, 잘못된 명령줄 옵션 등으로 작업에 실패하면 quickthumb는 공통 형식의 오류 상세 정보를 제공합니다. 에이전트는 설명 문장을 해석하지 않고도 문제의 입력과 해결 방법을 찾을 수 있습니다. 사람이 읽을 때는 한 줄 메시지로 원인을 확인할 수 있습니다.

## 오류 상세 필드 { #error-detail-fields }

| 필드 | 자료형 | 의미 |
| --- | --- | --- |
| `code` | 문자열 | 실패 종류의 안정적인 식별자. [코드 목록](#error-codes)을 참고하세요. |
| `category` | 문자열 | `validation`, `asset`, `export`, `input` 중 하나 |
| `message` | 문자열 | 사람이 읽을 수 있는 실패 설명 |
| `path` | 문자열 또는 `null` | 문서 내 위치가 있는 실패일 때 입력 문서의 [RFC 6901 JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901) |
| `layer_id` | 문자열 또는 `null` | 알 수 있는 경우 `path`를 포함하는 가장 안쪽 레이어 ID |
| `suggestion` | 문자열 또는 `null` | 알 수 있는 경우 구체적인 해결 방법 |

`path`는 현재 읽거나 검증하는 문서 안에서 문제가 생긴 위치를 가리킵니다.
`Canvas.from_json`, `Deck.from_json`, `validate()`, CLI에서는 문서 루트가 기준이므로 Deck 실패는 `/slides/<index>`로 시작합니다.
`TextLayer(...)`처럼 Python에서 직접 만든 모델은 해당 모델을 기준으로 합니다.

## Python API { #python-api }

모든 quickthumb 예외는 `QuickthumbError`에서 파생되며 같은 상세 정보를 제공합니다.

```python
from quickthumb import Canvas, QuickthumbError

try:
    Canvas.from_json(spec).render("out.png")
except QuickthumbError as error:
    for detail in error.details:
        print(detail.code, detail.path, detail.layer_id, detail.suggestion)
    print(error)  # "/layers/1/max_width (layer 'title'): max_width must be positive"
```

| 예외 | 범주 | 발생 원인 |
| --- | --- | --- |
| `ValidationError` | `validation` | 잘못된 JSON, 알 수 없거나 누락된 필드, 잘못된 값 |
| `MissingAssetError` | `asset` | 로컬 이미지, SVG, 동영상, 텍스트 채우기, 오디오 파일이 없음. `FileNotFoundError`이기도 합니다. |
| `RenderingError` | `export` | 지원하지 않는 출력 형식, 대상이 내보낼 수 없는 기능, 렌더러 실패 |
| `InputError` | `input` | 잘못된 명령줄 옵션, 읽을 수 없는 명세 파일 |

`Canvas.validate()`와 `Deck.validate()`도 `ValidationReport.errors`에 같은 `ErrorDetail` 레코드를 반환하므로 사전 검사와 렌더링 실패가 문제를 같은 방식으로 설명합니다.

## CLI { #cli }

`quickthumb render`는 `--error-format json`을, `quickthumb lint`와 `quickthumb diagnose`는 `--format json`을 받습니다.
실패는 모든 상세 필드가 있는 결과 하나로 stdout에 기록됩니다.

```bash
quickthumb render spec.json -o out.png --error-format json
```

```json
{
  "errors": [
    {
      "code": "asset_missing",
      "category": "asset",
      "message": "Asset not found: 'hero.png'",
      "path": "/slides/1/layers/0/path",
      "layer_id": "hero",
      "suggestion": "check the path relative to the working directory or use an http(s) URL"
    }
  ]
}
```

텍스트 모드는 상세 항목마다 코드로 시작하는 한 줄을 stderr에 출력합니다.

```text
error[asset_missing] /slides/1/layers/0/path (layer 'hero'): Asset not found: 'hero.png'. Suggestion: check the path relative to the working directory or use an http(s) URL.
```

종료 코드는 범주에 따릅니다. `export` 실패는 `2`, `validation`, `asset`, `input` 실패는 `1`입니다.

## 오류 코드 {#error-codes}

| 코드 | 범주 | 의미 |
| --- | --- | --- |
| `invalid_json` | `validation` | 유효한 JSON이 아닌 문서 |
| `invalid_document` | `validation` | 슬라이드 없는 Deck 등 구조적으로 사용할 수 없는 문서 |
| `invalid_field` | `validation` | 자료형이 다르거나 범위를 벗어난 필드 값 |
| `missing_field` | `validation` | 필수 필드 누락 |
| `unknown_field` | `validation` | 스키마에 없는 필드 |
| `unknown_plugin` | `validation` | 등록하지 않은 렌더러를 지정한 플러그인 레이어 |
| `asset_missing` | `asset` | 참조한 로컬 파일이 없음 |
| `unsupported_format` | `export` | 출력 확장자가 내보내기 형식이 아님 |
| `unsupported_capability` | `export` | 문서가 요구한 작업을 대상에서 할 수 없음. 플러그인 레이어를 렌더링하거나(quickthumb는 플러그인 레이어를 검증할 수 있지만 아직 그릴 수 없음), 필요한 대체 표현을 `ExportPolicy(unsupported_motion="error")` 같은 정책이 금지한 경우입니다. |
| `missing_dependency` | `export` | FFmpeg 같은 외부 도구를 사용할 수 없음 |
| `export_failed` | `export` | 기록할 수 없는 출력 경로를 포함한 나머지 내보내기·렌더링 실패 |
| `invalid_option` | `input` | 잘못된 명령줄 옵션 값 |
| `input_unreadable` | `input` | 명세 파일을 읽을 수 없음 |
| `unresolved_variable` | `input` | `$KEY` 자리표시자에 대응하는 `--var`가 없음 |

코드는 안정적입니다. 메시지 문구는 바뀔 수 있으므로 자동화는 `message` 대신 `code`와 `path`로 분기해야 합니다.
