# -
아름다운

## 박자 탭 (BeatTap)

버튼을 누른 간격이 기준 BPM으로 몇 박인지 알려주는 안드로이드 앱.

- **TAP**: 누를 때마다 직전 탭과의 간격을 박 수로 표시 (크게 1/4박 단위 반올림, 작게 실제 값과 ms)
- **박자 리셋**: 탭 기록 초기화 (다음 탭부터 새로 시작)
- **BPM**: 기본 120. `−`/`+` 로 ±1, 길게 누르면 ±10, 숫자를 누르면 직접 입력

### 빌드

```
./gradlew assembleDebug
# -> app/build/outputs/apk/debug/app-debug.apk
```

Android SDK 35, JDK 17+ 필요 (`local.properties`에 `sdk.dir` 지정).
