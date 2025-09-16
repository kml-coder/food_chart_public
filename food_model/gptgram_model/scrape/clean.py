import json

# 파일 경로 설정
input_file = "ingredients.json"
output_file = "output.json"
duplicates_file = "duplicates.json"

# 입력 파일에서 데이터 읽기
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 중복 제거 준비
seen = set()
result = []
duplicates = []

for item in data:
    key = (item["unit"], item["size"], item["name"])
    if key not in seen:
        seen.add(key)
        # 복사해서 original 제거하고 저장
        new_item = item.copy()
        new_item.pop("original", None)
        result.append(new_item)
    else:
        duplicates.append(item)  # original 포함 상태로 저장

# duplicates 정렬
duplicates.sort(key=lambda x: (x["unit"], x["size"], x["name"]))

# 결과 저장
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

with open(duplicates_file, "w", encoding="utf-8") as f:
    json.dump(duplicates, f, ensure_ascii=False, indent=2)

print(f"✅ 처리 완료!")
print(f" - 정제된 데이터: {output_file}")
print(f" - 정렬된 중복 항목: {duplicates_file} (총 {len(duplicates)}개)")
