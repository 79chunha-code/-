# 화원태왕타운 단지 모델

대구 달성군 화원읍 화원태왕타운(9개 동, 9~18층, 1995년 준공)을 게임용으로 만든 3D 모델입니다.

- 동 배치는 지도에서 잰 좌표를 씁니다.
- 외벽 색과 생김새는 2026년 7월 네이버 거리뷰를 참고했습니다 (남색·회색·흰색 도색).
- 텍스처는 전부 코드로 그립니다. 실제 사진이나 지도 이미지는 모델에 들어가지 않습니다.
- 상가 간판 글자는 실제 가게 이름이 아니라 흔한 업종 이름을 무작위로 넣은 것입니다.

## 결과물
- `assets/models/hwawon_taewang.glb`: 게임 엔진(Godot 등)에서 바로 쓰는 파일
- `assets/models/hwawon_taewang.blend`: Blender 원본 (텍스처 포함)
- `assets/textures/hwawon_taewang/`: 텍스처 (색 / `_orm` 거칠기 / `_n` 노멀맵)
- `docs/renders/`: 미리보기 이미지

## 들어 있는 것
- 아파트 9개 동: 둥근 발코니, 계단실, 옥탑, 공동현관 캐노피(파란 기와), 동 번호
- 주차장과 차량, 과속방지턱, 바닥 글씨, 화단, 생울타리
- 벽돌 담장(구멍 뚫린 무늬), 강돌 문기둥, 정문 팔각 경비실, 동별 경비실
- 소나무, 활엽수, 하천변 메타세쿼이아
- 정자, 놀이터, 자전거 보관대, 분리수거장, 가로등, 전봇대와 전선
- 정문 옆 상가, 하천과 보행교, 주변 창고·상가·주택, 건너편 고층 아파트

## 다시 만들기
```bash
pip install bpy pillow numpy
apt-get install -y fonts-nanum        # 간판과 바닥 글씨용 한글 글꼴
python3 tools/blender/hwawon_taewang/textures.py assets/textures/hwawon_taewang
python3 tools/blender/hwawon_taewang/build.py --tex assets/textures/hwawon_taewang --out assets/models
# 렌더까지: --render docs/renders --views aerial,south_st --samples 40
```

## 파일 구성
| 파일 | 하는 일 |
|---|---|
| `textures.py` | 텍스처 생성 (PIL, numpy) |
| `lib.py` | 좌표 변환, 재질, 메시 빌더 |
| `apartments.py` | 아파트 동. 배치·층수·색은 `BUILDINGS`에서 바꿈 |
| `site_build.py` | 바닥, 도로, 주차장, 담장, 정문, 상가, 하천, 주변 건물 |
| `props.py` | 나무, 자동차, 경비실 등 소품 |
| `build.py` | 전체 조립, 내보내기, 렌더 |

## 좌표
- 단위 m, X = 동쪽, Y = 북쪽, Z = 위 (glb로 내보내면 Y가 위로 바뀜)
- `lib.geo(경도, 위도)`로 실제 좌표를 모델 좌표로 바꿀 수 있음 (오차 몇 m)

## 아직 추정인 부분
- 동별 정확한 층수, 세대 평면, 발코니 위치
- 단지 안 화단과 주차 칸의 정확한 위치
- 주변 건물은 분위기만 맞춘 것이고 실제 건물과 다름
