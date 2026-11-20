# 천사 모델 프롬프트 (Gemini용)

## 지금 쓰는 것: 한국어, 직접 정한 묘사만

천사를 정할 때 직접 말하거나 고른 것만 모았다. 치수, 노드 이름 같은 기술 규칙은 넣지 않았다.

```text
성경 속 천사 같은 보스를 3D로 만들어 줘. 결과는 .glb 파일 하나로 줘.

- 느낌: 성스럽고 아름다우면서, 이질적이고 무서운 존재.
- 크기: 아주 크다. 키 6.5m.
- 머리 대신 거대한 눈알 하나가 목 근처 위에 떠 있다. 이 눈알은 사실적으로: 맨 눈알, 하늘색 홍채, 흰자에 엷은 핏줄.
- 눈알은 아주 크게, 몸통은 아주 작게. 눈알과 몸통이 1:1 비율.
- 몸: 긴 로브, 밑단은 종처럼 퍼진다. 다리는 안 보이고 팔은 없다.
- 로브 장식은 하늘색 테두리만. 깃 안에서 빛이 새어 나온다.
- 색: 몸과 눈은 흰색과 하늘색. 금색은 빛에만 쓴다 (눈알 뒤의 후광, 깃 안의 빛).
- 고리: 행성처럼 눈알을 감고 있는 기울어진 고리 하나. 속이 빈 짧은 원통(낮은 띠)이고, 작고 둥근 눈알 12개 안팎이 반쯤 박혀 있다.
- 가운데 눈알은 사실적으로, 주변의 눈알들은 그보다 단순하게.
- 날개: 세 쌍. 크고, 거의 수평으로 펼쳐진다. 겹겹이 쌓인 둥근 깃털.
- 날개의 눈: 날개에 눈이 아주 많은 느낌. 눈은 바깥쪽 큰 깃털에만, 깃털 무늬처럼 그려진 눈으로.
- 날개 눈은 다칠 때마다 하나씩 감긴다. 그래서 눈마다 감긴 모습(속눈썹 달린 곡선)도 따로 있어야 한다.
- 후광: 눈알 뒤에서 금빛이 나온다. 해처럼 빛살이 퍼지지만 너무 많이 퍼지지 않게. 그림으로 그린 원판이 아니라 진짜 빛처럼, 눈알과 고리와 깃털이 가린 모양대로 빛줄기가 새어 나와야 한다. 손가락 사이로 빛이 새는 것처럼.
- 움직임: 천천히 오르내리고, 고리가 돌고, 날개가 펄럭인다.
- 전체적으로 매끈하고 정교하게. 너무 단순해 보이지 않게.
```

---

## 이전 버전: 영어, 치수와 게임 연결 규칙까지 (첫 번째로 시도한 것)

지금 천사(tools/character/angel.py, assets/characters/angel.glb)의 틀과 치수를 그대로 두고, 세부를 더 정교하게 다시 만들게 하는 프롬프트.
아래 "PROMPT" 줄부터 끝까지 그대로 붙여 넣으면 된다. 뒤쪽 "Technical requirements"는 전투 화면(game/battle3d)에 바로 꽂기 위한 규칙이다.

---

PROMPT

Build a 3D model of a biblical-style angel boss for a web game, and export it as a single binary glTF 2.0 file (.glb). Write the geometry with code the way you would build an architectural model: careful proportions, clean shapes, many parts, flat PBR colours. Do not use image textures; make every detail (iris, veins, eyes on the wings) from geometry and materials.

## The idea

A towering being that is holy and beautiful, and also alien and frightening. Instead of a head it has one enormous floating eyeball. It has no arms and no legs. Its body is a small white robe; the eye is as big as the whole body. Three pairs of huge white wings spread almost flat to the sides, and their large outer feathers carry painted eyes. A ring like Saturn's, made of a short hollow band with twelve small eyeballs sunk into it, circles the big eye. A gold light shines from behind the eye and from inside the collar.

Keep the proportions and parts below exactly. Within them, add as much refinement as you can: softer folds, layered feathers, bevels, small trims.

## Overall size and axes

- Units are metres. Y is up. The angel faces +Z (toward the viewer). X is its left-right.
- The bottom of the robe's hem is at y = 0, centred on x = 0, z = 0. The whole figure floats in the game, so nothing touches the ground.
- Total height about 6.1 m (top of the upper wings). Wingspan about 12.4 m (x from -6.2 to +6.2). Depth about 4.5 m.

## Robe (body)

- A long bell-shaped robe with no visible legs or arms, standing 2.4 m from hem (y = 0) to collar (y = 2.4).
- Radius of the robe at each height (front-to-back depth is 92% of the width):
  y 0.00 → 0.78, y 0.17 → 0.71, y 0.40 → 0.60, y 0.66 → 0.49, y 1.00 → 0.39, y 1.33 → 0.34 (slim waist), y 1.62 → 0.32, y 1.89 → 0.36, y 2.12 → 0.42 (rounded shoulders), y 2.27 → 0.41, y 2.35 → 0.32, y 2.40 → 0.21 (collar opening).
- About 16 soft vertical folds, deepest at the hem and fading out by the waist.
- A sky-blue band about 0.1 m tall at the hem, and a rolled sky-blue collar (a small torus) at the top. Only these trims are blue; the rest is white.
- The inside of the bell is lined in a darker blue-white, visible from below.
- Gold light pours out of the collar opening: a glowing gold well inside the collar and a faint, short, translucent gold cone rising from it (emissive).

## The central eye (the head)

- One realistic eyeball, radius 1.2 m (2.4 m across), floating just above the collar: its centre is at (0, 3.72, 0), leaving a 0.12 m gap above the collar.
- Facing +Z. Build it from layers instead of a texture:
  - a white sclera sphere, very slightly blue-grey toward the back,
  - faint thin veins on the sclera: very thin, slightly raised pale red-pink curves, sparse, mostly near the edges,
  - a sky-blue iris (about 47% of the eye's radius across the front), slightly concave, made of concentric rings of lighter and darker sky blue plus fine radial ridges, with a lighter ring around the pupil,
  - a black pupil (about 17% of the radius),
  - a clear glossy cornea dome over the iris (transparent, high gloss).

## The ring of eyes

- Centred on the big eye. A short hollow cylinder (a low band, not a torus): outer radius 2.04 m, band height 0.52 m, wall thickness 0.07 m.
- Outer and inner faces white (inner face shaded a little darker), top and bottom rims sky blue.
- Twelve small eyeballs, radius 0.23 m, evenly spaced around the band, each sunk halfway into the outer face and looking straight outward. Each sits in a sky-blue socket rim. Make them simpler than the central eye: white ball, sky-blue iris, black pupil.
- The ring is tipped like Saturn's ring, nearly flat: tilt it with the rotation quaternion (x, y, z, w) = (0.1549, 0.0218, 0.1375, 0.9781) (about 18° toward the viewer and 16° to the side).

## Wings (three pairs)

Each wing has a root point (pivot) near the upper back of the robe and extends outward. Values are for the right wing (+X); the left wing is an exact mirror (negate x).

| Pair | Pivot (x, y, z) | Raised above horizontal | Swept back | Length | Feather droop |
|---|---|---|---|---|---|
| Top | (0.24, 2.32, -0.30) | 30° | 10° | 4.2 m | 72° |
| Mid | (0.30, 2.04, -0.34) | 4° | 14° | 3.6 m | 75° |
| Low | (0.28, 1.76, -0.30) | -20° (slightly down) | 12° | 2.9 m | 62° |

- Each wing's arm is a gentle upward arch from the root to the tip (the middle rises about 0.18 × length).
- Feathers are layered, rounded at the tip, slightly curved, with a thin raised shaft. White, fading to pale sky blue toward the tips. Their front faces face +Z.
  - 7 long primary feathers fan out from the outer half of the arm and hang down from it: the outermost almost along the arm, the innermost drooping by the "feather droop" angle. Each primary is about 0.55 × wing length long (getting slightly shorter inward) and 0.115 × wing length wide.
  - 8 shorter secondary feathers along the inner half, hanging further down.
  - 2 rows of small covert feathers over the bases (about 12 and 14 feathers).
- The three pairs together read as a wide, nearly flat fan behind the body, upper pair largest.

## Eyes on the wings

- Only on the 7 long primary feathers of each wing: 7 per wing, 42 in total.
- Each sits about two thirds of the way along its feather, lying across it (wider than tall: width about 0.84 × the feather's width, height half of that), floating 1–2 cm in front of the feather's surface.
- They are simple, like eyes painted on the feathers, not realistic: an almond-shaped white shape, a sky-blue iris disc, a dark pupil, and a thin dark outline.
- Every eye has two versions in the same place:
  - Open: the almond eye described above.
  - Closed: a single gently curved dark eyelid line with 5–7 short lashes, placed just behind the open eye (about 3 mm further back), so that when the game hides the open eye, the closed one shows.

## Light behind the eye

- Do not model a halo disc or light rays. Only mark where the light is: an empty node 1.55 m directly behind the centre of the big eye (see the names below). The game draws the light there.

## Colours and materials (PBR, no textures)

| Material name | Use | Colour | Notes |
|---|---|---|---|
| angel_white | robe, ring faces, feathers | #f4f6fb | roughness ~0.6 |
| angel_white_shade | robe lining, inner ring face | #c9d4ea / #9fb0d2 | |
| angel_sky | hem band, collar, ring rims, sockets, feather tips | #7fb8ec (darker #4f8fd6 for edges) | |
| angel_eye | central eye sclera | white | roughness ~0.35 |
| angel_iris | irises | sky blue, several shades | |
| angel_pupil | pupils, lash lines | near black #0d1020 | |
| angel_cornea | cornea dome | clear | transparent, roughness ~0.05 |
| angel_vein | sclera veins | pale red-pink | |
| angel_collar_light | light in the collar | #ffd27a | emissive, strength ~6 |

Gold is used only for light. The body and the eyes stay white and sky blue.

## Technical requirements (for the game, follow exactly)

1. Do NOT merge everything into one mesh. Keep this node hierarchy with these exact names (names are case-sensitive):

```
Angel                                  (root, origin at the hem centre (0,0,0), no rotation)
├─ Angel_Robe                          (mesh)
├─ Angel_RobeLining                    (mesh)
├─ Angel_CollarLight                   (mesh, emissive)
├─ Angel_Head                          (empty at (0, 3.72, 0), no rotation)
│  ├─ Angel_Eye                        (ONE mesh for the whole central eye, origin at the eye's centre, looking down +Z, no rotation)
│  ├─ Angel_HaloLight                  (empty at (0, 0, -1.55) relative to Angel_Head)
│  └─ Angel_RingTilt                   (empty at the head's origin, rotation = the quaternion above)
│     └─ Angel_Ring                    (empty, no rotation; the game spins it around its local Y axis)
│        ├─ Angel_RingBand             (mesh: band and sockets)
│        └─ Angel_RingEye_00 … _11     (12 meshes, each origin at its eyeball's centre on the band at radius 2.04,
│                                       evenly spaced around local Y, each looking outward)
└─ Angel_WingPivot_RTop, _RMid, _RLow, _LTop, _LMid, _LLow
                                       (empties at the pivot points, rotated so the wing points along their local axis)
   └─ Angel_Wing_RTop (etc.)           (ONE mesh per wing with all its feathers; origin at the pivot)
      ├─ Angel_WingEyeOpen_RTop_0 … _6    (7 separate meshes)
      └─ Angel_WingEyeClosed_RTop_0 … _6  (7 separate meshes)
```

2. Each wing eye (open and closed) is its own mesh with its origin at the centre of that eye, its local +Z facing out of the feather and its local Y running along the feather (the eye's height). The game closes an eye by squashing the open one's local Y to zero or hiding it.
3. A single mesh node can hold several materials (several primitives), but keep the central eye as one node and each wing as one node.
4. Keep every transform clean: no scale on any node (scale 1), no rotation except Angel_RingTilt, the six wing pivots and each Angel_RingEye.
5. Triangle budget: 40,000 to 90,000 triangles in total. Spend them on the central eye, the feathers and the robe's silhouette.
6. Animation is optional. If you add any, make one 8-second looping clip named "Idle" that only moves the root (a slow 0.1 m bob), Angel_Head (a smaller bob) and the six Angel_Wing_* nodes (slow, offset flaps of a few degrees). Never animate Angel_Eye, Angel_Ring, Angel_RingTilt or the wing pivots; the game controls those.
7. Export: one .glb, glTF 2.0, Y-up, metres, materials as plain PBR (metallic-roughness), no image textures, no lights or cameras in the file.

## Before you finish, check and print

- the overall bounding box (should be about x -6.2…6.2, y 0…6.1, z -2.3…2.3),
- the total triangle count,
- every node name in the hierarchy above, and confirm each exists exactly once,
- that there are 12 Angel_RingEye nodes, 42 Angel_WingEyeOpen nodes and 42 Angel_WingEyeClosed nodes.
