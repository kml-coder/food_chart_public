# Model Details

## Model Strategy

- 대형 오픈 LLM도 가능하지만, 이 문제에는 비용/용량 대비 과한 선택
- 도메인 특화 경량 모델을 직접 학습해서 배포 효율 확보
- baseline 비교 후 `t5-small` 중심으로 실험, 서버에는 `DeBERTa` 경로도 포함

실험 기록(대표값):

- usable rows: `18,262` / `18,136` / `25,983`
- Parse success rate: `1.0000`
- MAE: `55.1919 g`
- MAPE: `175.99%`
- Within 20%: `0.5809`
- Robust MAE: `29.8048 g`

> 데이터 버전/실험 조건에 따라 지표는 변동됩니다.

---

## Model Artifacts

- Local T5 model 다운로드: [Google Drive](https://drive.google.com/file/d/1_l-JuXDqZ-0Qd15OYCNO-n60bmftbety/view?usp=drive_link)
- 서버 로딩 경로: `food_server/model`
- DeBERTa 경로: `DEBERTA_MODEL_PATH` 환경변수
- Hugging Face 공개 시 추가 예정:
  - `https://huggingface.co/<your-org-or-id>/<model-repo>`

---

## Documentation

모델 제작/실험 상세는 아래 문서에서 확인할 수 있습니다.

- `food_model/gptgram_model/scrape/unit_size_cleanup.ipynb`
- `food_model/gptgram_model/t5_small_regression.ipynb`

---

## Known Limits

- 레시피 사이트별 파싱 품질 편차 존재
- unit이 없는 라인/비정형 라인은 모델 추론 의존도 높음
- 일부 재료는 동일 이름이라도 맥락별 무게 편차가 큼
