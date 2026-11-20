package com.beattap;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.InputType;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.ListView;
import android.widget.TextView;

import java.util.Locale;

public class MainActivity extends Activity {

    private static final int DEFAULT_BPM = 120;
    private static final int MIN_BPM = 20;
    private static final int MAX_BPM = 400;
    /** 반올림 단위: 1/4박 (16분음표) */
    private static final double ROUND_STEP = 0.25;
    /** 기록 최대 개수 (넘으면 가장 오래된 것부터 지움) */
    private static final int MAX_HISTORY = 1000;

    private int bpm = DEFAULT_BPM;
    /** 마지막 탭 시각 (SystemClock.uptimeMillis 기준), -1 = 아직 없음 */
    private long lastTapTime = -1;
    private int intervalCount = 0;

    private TextView bpmText, beatText, detailText;
    private ListView historyList;
    private ArrayAdapter<String> historyAdapter;
    private SharedPreferences prefs;

    @SuppressLint("ClickableViewAccessibility")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        bpmText = findViewById(R.id.bpmText);
        beatText = findViewById(R.id.beatText);
        detailText = findViewById(R.id.detailText);
        historyList = findViewById(R.id.historyList);
        historyAdapter = new ArrayAdapter<>(this, R.layout.history_item);
        historyList.setAdapter(historyAdapter);

        prefs = getSharedPreferences("beattap", MODE_PRIVATE);
        bpm = clampBpm(prefs.getInt("bpm", DEFAULT_BPM));

        // 손가락이 닿는 순간(ACTION_DOWN)을 기준으로 측정해야 타이밍이 정확함
        TextView tap = findViewById(R.id.tapButton);
        tap.setOnTouchListener((v, e) -> {
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                case MotionEvent.ACTION_POINTER_DOWN:
                    v.setPressed(true);
                    v.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY);
                    onTap(e.getEventTime());
                    return true;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    v.setPressed(false);
                    return true;
                default:
                    return true;
            }
        });

        findViewById(R.id.resetButton).setOnClickListener(v -> resetBeat());

        findViewById(R.id.bpmMinus).setOnClickListener(v -> setBpm(bpm - 1));
        findViewById(R.id.bpmPlus).setOnClickListener(v -> setBpm(bpm + 1));
        findViewById(R.id.bpmMinus).setOnLongClickListener(v -> { setBpm(bpm - 10); return true; });
        findViewById(R.id.bpmPlus).setOnLongClickListener(v -> { setBpm(bpm + 10); return true; });
        bpmText.setOnClickListener(v -> showBpmDialog());

        updateBpmText();
        resetBeat();
    }

    private void onTap(long time) {
        if (lastTapTime < 0) {
            lastTapTime = time;
            beatText.setText("시작!");
            detailText.setText("다음 타이밍에 눌러주세요");
            return;
        }

        long ms = time - lastTapTime;
        lastTapTime = time;
        intervalCount++;

        double beats = ms * bpm / 60000.0;
        double rounded = Math.round(beats / ROUND_STEP) * ROUND_STEP;
        if (rounded < ROUND_STEP) rounded = ROUND_STEP;

        beatText.setText(formatBeats(rounded) + "박");
        detailText.setText(String.format(Locale.US, "실제 %.2f박 · %dms", beats, ms));

        // 최신 기록이 맨 위
        historyAdapter.insert(String.format(Locale.US, "#%-4d %6s박  (%.2f)",
                intervalCount, formatBeats(rounded), beats), 0);
        while (historyAdapter.getCount() > MAX_HISTORY) {
            historyAdapter.remove(historyAdapter.getItem(historyAdapter.getCount() - 1));
        }
        historyList.setSelection(0);
    }

    private void resetBeat() {
        lastTapTime = -1;
        intervalCount = 0;
        historyAdapter.clear();
        beatText.setText("—");
        detailText.setText("TAP을 눌러 시작하세요");
    }

    private void setBpm(int value) {
        bpm = clampBpm(value);
        prefs.edit().putInt("bpm", bpm).apply();
        updateBpmText();
    }

    private void updateBpmText() {
        bpmText.setText("♩ = " + bpm + " BPM");
    }

    private void showBpmDialog() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER);
        input.setText(String.valueOf(bpm));
        input.setSelectAllOnFocus(true);
        new AlertDialog.Builder(this)
                .setTitle("BPM 입력 (" + MIN_BPM + "~" + MAX_BPM + ")")
                .setView(input)
                .setPositiveButton("확인", (d, w) -> {
                    try {
                        setBpm(Integer.parseInt(input.getText().toString().trim()));
                    } catch (NumberFormatException ignored) {
                    }
                })
                .setNeutralButton("120으로", (d, w) -> setBpm(DEFAULT_BPM))
                .setNegativeButton("취소", null)
                .show();
        input.requestFocus();
    }

    private static int clampBpm(int v) {
        return Math.max(MIN_BPM, Math.min(MAX_BPM, v));
    }

    /** 1.0 -> "1", 1.5 -> "1.5", 0.25 -> "0.25" */
    private static String formatBeats(double v) {
        if (v == Math.floor(v)) return String.valueOf((long) v);
        String s = String.format(Locale.US, "%.2f", v);
        while (s.endsWith("0")) s = s.substring(0, s.length() - 1);
        return s;
    }
}
