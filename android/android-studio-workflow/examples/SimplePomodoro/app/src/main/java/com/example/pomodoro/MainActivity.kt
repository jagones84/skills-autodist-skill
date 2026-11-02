package com.example.pomodoro

import android.os.Bundle
import android.os.CountDownTimer
import android.os.Vibrator
import android.os.VibrationEffect
import android.os.Build
import android.content.Context
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var timerText: TextView
    private lateinit var startBtn: Button
    private lateinit var resetBtn: Button
    private lateinit var vibrator: Vibrator

    private var countdown: CountDownTimer? = null
    private var isWork = true
    private var remaining = WORK_MS

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        timerText = findViewById(R.id.timerText)
        startBtn = findViewById(R.id.startBtn)
        resetBtn = findViewById(R.id.resetBtn)

        vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as android.os.VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }

        startBtn.setOnClickListener { toggle() }
        resetBtn.setOnClickListener { reset() }
        updateLabel()
    }

    private fun toggle() {
        if (countdown != null) {
            countdown?.cancel()
            countdown = null
            startBtn.text = "Start"
        } else {
            startTimer(remaining)
            startBtn.text = "Pausa"
        }
    }

    private fun startTimer(ms: Long) {
        countdown = object : CountDownTimer(ms, 1000) {
            override fun onTick(millisUntilFinished: Long) {
                remaining = millisUntilFinished
                val sec = (millisUntilFinished / 1000).toInt()
                val m = sec / 60
                val s = sec % 60
                timerText.text = String.format("%02d:%02d", m, s)
            }
            override fun onFinish() {
                vibrate()
                isWork = !isWork
                remaining = if (isWork) WORK_MS else BREAK_MS
                updateLabel()
                countdown = null
                startBtn.text = "Start"
            }
        }.start()
    }

    private fun reset() {
        countdown?.cancel()
        countdown = null
        isWork = true
        remaining = WORK_MS
        updateLabel()
        startBtn.text = "Start"
    }

    private fun updateLabel() {
        val sec = (remaining / 1000).toInt()
        val m = sec / 60
        val s = sec % 60
        timerText.text = String.format("%02d:%02d", m, s)
        timerText.contentDescription = if (isWork) "Work" else "Break"
    }

    private fun vibrate() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 300, 100, 300, 100, 500), -1))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(longArrayOf(0, 300, 100, 300, 100, 500), -1)
        }
    }

    override fun onDestroy() {
        countdown?.cancel()
        super.onDestroy()
    }

    companion object {
        private const val WORK_MS = 25 * 60 * 1000L
        private const val BREAK_MS = 5 * 60 * 1000L
    }
}
