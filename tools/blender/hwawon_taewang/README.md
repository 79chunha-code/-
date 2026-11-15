# 화원태왕타운 단지 모델

대구 달성군 화원읍 화원태왕타운(9개 동, 9~18층, 1995년 준공)을 로우폴리로 만든 모델입니다.
동 배치는 지도에서 읽은 좌표를 쓰고, 외벽은 로드뷰를 참고해 코드로 그린 텍스처를 씁니다.
실제 사진은 모델에 들어가지 않습니다.

## 결과물
- `assets/models/hwawon_taewang.glb`: 게임 엔진(Godot 등)에서 바로 쓰는 파일
- `assets/models/hwawon_taewang.blend`: Blender 원본
- `docs/renders/`: 미리보기 이미지

## 다시 만들기
```bash
pip install bpy pillow
python3 tools/blender/hwawon_taewang/textures.py assets/textures/hwawon_taewang
python3 tools/blender/hwawon_taewang/build.py --tex assets/textures/hwawon_taewang --out assets/models
# 렌더까지: --render docs/renders --samples 40
```

## 좌표
- 단위 m, X = 동쪽, Y = 북쪽, Z = 위 (glb로 내보내면 Y가 위로 바뀜)
- `Entrance_<동>_<번호>` 빈 오브젝트: 공동현관 앞 위치 (게임에서 스폰/이벤트 지점으로 쓸 수 있음)
- 동 배치, 층수, 세그먼트 수는 `build.py`의 `BUILDINGS`에서 바꿀 수 있음
