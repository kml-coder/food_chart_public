# Data Pipeline

## 1) Collect

- 레시피 사이트에서 재료 라인 수집
- URL 입력과 텍스트 입력 모두 처리 가능

## 2) Clean

`food_model/gptgram_model/scrape/unit_size_cleanup.ipynb` 기준:

- `small|medium|large`를 `unit`에서 분리
- `thin slice`/`thick slice`를 `slice`로 정규화
- 다단어 unit 제거
- `name` 내부 unit 중복 토큰 제거

산출 요약:

- Source rows: `18,352` (`output_filled.json`)
- Clean rows: `18,221` (`output_filled_name_unit_removed.json`)
- size 정리/이동: `155`
- `slice` 정규화: `102`
- 다단어 unit 제거: `130`
- name 내부 unit 정리: `34`

## 3) Enrich

- 부족한 unit/재료 표현은 외부 데이터로 보강
- USDA 데이터는 첫 번째 콤마 이전 문자열(짧은 이름) 기준으로 정규화
- 정확도 향상을 위해 일부 구간은 `ChatGPT API`로 데이터 채움

> 공개 JSON에는 recipe ID가 없어 현재는 레시피 수가 아니라 재료 row 수 기준으로 관리합니다.
