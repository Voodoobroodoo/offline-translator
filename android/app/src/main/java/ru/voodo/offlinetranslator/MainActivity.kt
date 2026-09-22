package ru.voodo.offlinetranslator

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.languageid.LanguageIdentification
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.SpeechService

class MainActivity : AppCompatActivity() {

    private var translator: Translator? = null
    private val handler = Handler(Looper.getMainLooper())

    private lateinit var directionGroup: MaterialButtonToggleGroup
    private lateinit var source: EditText
    private lateinit var output: TextView
    private lateinit var status: TextView
    private lateinit var chipText: TextView
    private lateinit var chipVoiceRu: TextView
    private lateinit var chipVoiceEn: TextView
    private lateinit var micBtn: Button

    // Vosk
    private var voskModel: Model? = null
    private var speechService: SpeechService? = null
    private var listening = false
    private var micLangAfterPermission: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        directionGroup = findViewById(R.id.directionGroup)
        source = findViewById(R.id.source)
        output = findViewById(R.id.output)
        status = findViewById(R.id.status)
        chipText = findViewById(R.id.chipText)
        chipVoiceRu = findViewById(R.id.chipVoiceRu)
        chipVoiceEn = findViewById(R.id.chipVoiceEn)
        micBtn = findViewById(R.id.micBtn)
        val translateBtn = findViewById<Button>(R.id.translateBtn)
        val copyBtn = findViewById<Button>(R.id.copyBtn)
        val swapBtn = findViewById<Button>(R.id.swapBtn)
        val modelsBtn = findViewById<Button>(R.id.modelsBtn)

        chipText.setOnClickListener {
            status.text = getString(R.string.downloading_text)
            downloadTextModels { refreshChips() }
        }
        chipVoiceRu.setOnClickListener { startVoiceDownload("ru") }
        chipVoiceEn.setOnClickListener { startVoiceDownload("en") }
        modelsBtn.setOnClickListener {
            downloadModels { status.text = getString(R.string.models_ready) }
        }

        micBtn.setOnClickListener {
            if (listening) {
                stopListening()
                status.text = getString(R.string.hint_models)
            } else {
                startMicFlow()
            }
        }

        translateBtn.setOnClickListener {
            val text = source.text.toString().trim()
            if (text.isEmpty()) {
                status.text = getString(R.string.empty_input)
                return@setOnClickListener
            }
            translateSmart(text)
        }

        copyBtn.setOnClickListener {
            val text = output.text.toString()
            if (text.isNotBlank()) {
                val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("translation", text))
                Toast.makeText(this, R.string.copied, Toast.LENGTH_SHORT).show()
            }
        }

        swapBtn.setOnClickListener {
            val src = source.text.toString()
            val dst = output.text.toString()
            source.setText(dst)
            output.text = src
            val checked = directionGroup.checkedButtonId
            if (checked == R.id.btnEnRu) {
                directionGroup.check(R.id.btnRuEn)
            } else if (checked == R.id.btnRuEn) {
                directionGroup.check(R.id.btnEnRu)
            }
            status.text = getString(R.string.swapped)
        }

        status.text = getString(R.string.hint_models)

        // «Поделиться → Офлайн-переводчик» из других приложений
        val shared = intent?.takeIf { it.action == Intent.ACTION_SEND }?.getStringExtra(Intent.EXTRA_TEXT)
        if (!shared.isNullOrBlank()) {
            source.setText(shared)
            status.text = getString(R.string.shared_hint)
            translateSmart(shared)
        }
    }

    override fun onResume() {
        super.onResume()
        refreshChips()
    }

    // ---------------- Готовность компонентов ----------------

    private fun refreshChips() {
        // Текстовые модели (ML Kit)
        RemoteModelManager.getInstance()
            .getDownloadedModels(TranslateRemoteModel::class.java)
            .addOnSuccessListener { downloaded ->
                val codes = downloaded.map { it.language }
                val ready = codes.containsAll(
                    listOf(TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN)
                )
                setChip(
                    chipText,
                    ready,
                    getString(R.string.chip_text_ready),
                    getString(R.string.chip_text_missing)
                )
            }

        // Голосовые модели (Vosk)
        setChip(
            chipVoiceRu,
            VoiceRepo.isDownloaded(this, "ru"),
            getString(R.string.chip_voice_ru_ready),
            getString(R.string.chip_voice_ru_missing)
        )
        setChip(
            chipVoiceEn,
            VoiceRepo.isDownloaded(this, "en"),
            getString(R.string.chip_voice_en_ready),
            getString(R.string.chip_voice_en_missing)
        )
    }

    private fun setChip(chip: TextView, ready: Boolean, readyText: String, missingText: String) {
        if (ready) {
            chip.text = readyText
            chip.backgroundTintList = ContextCompat.getColorStateList(this, R.color.green_bg)
            chip.setTextColor(ContextCompat.getColor(this, R.color.green))
        } else {
            chip.text = missingText
            chip.backgroundTintList = ContextCompat.getColorStateList(this, R.color.red_bg)
            chip.setTextColor(ContextCompat.getColor(this, R.color.red))
        }
    }

    private fun startVoiceDownload(lang: String) {
        if (VoiceRepo.isDownloaded(this, lang)) {
            refreshChips()
            return
        }
        val chip = if (lang == "ru") chipVoiceRu else chipVoiceEn
        chip.text = getString(R.string.downloading_voice)
        VoiceRepo.download(
            this, lang,
            {
                refreshChips()
                status.text = getString(R.string.voice_ready)
                status.setTextColor(ContextCompat.getColor(this, R.color.green))
            },
            { err ->
                status.text = getString(R.string.error, err)
                status.setTextColor(ContextCompat.getColor(this, R.color.red))
                refreshChips()
            }
        )
    }

    private fun downloadTextModels(onReady: () -> Unit) {
        val manager = RemoteModelManager.getInstance()
        val missing = mutableListOf<String>()
        val conditions = DownloadConditions.Builder().build()
        for (lang in listOf(TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN)) {
            val model = TranslateRemoteModel.Builder(lang).build()
            manager.download(model, conditions)
                .addOnSuccessListener {
                    missing.remove(lang)
                    if (missing.isEmpty()) {
                        refreshChips()
                        onReady()
                    }
                }
                .addOnFailureListener {
                    status.text = getString(R.string.download_failed, it.message)
                }
        }
    }

    private fun downloadModels(onReady: () -> Unit) {
        status.text = getString(R.string.downloading_text)
        downloadTextModels(onReady)
    }

    // ---------------- Микрофон и Vosk ----------------

    private fun startMicFlow() {
        val lang = when (directionGroup.checkedButtonId) {
            R.id.btnRuEn -> "ru"
            R.id.btnEnRu -> "en"
            else -> getPreferences(Context.MODE_PRIVATE).getString("voice_lang", null) ?: ""
        }
        if (lang.isEmpty()) {
            askMicLanguage { chosen ->
                getPreferences(Context.MODE_PRIVATE).edit().putString("voice_lang", chosen).apply()
                startMicWithPermission(chosen)
            }
        } else {
            startMicWithPermission(lang)
        }
    }

    private fun askMicLanguage(onChoose: (String) -> Unit) {
        val options = arrayOf(getString(R.string.mic_lang_ru), getString(R.string.mic_lang_en))
        AlertDialog.Builder(this)
            .setTitle(R.string.mic_pick_language)
            .setItems(options) { _, which ->
                onChoose(if (which == 0) "ru" else "en")
            }
            .show()
    }

    private fun startMicWithPermission(lang: String) {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startListening(lang)
        } else {
            micLangAfterPermission = lang
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.RECORD_AUDIO), 1001
            )
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1001 &&
            grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED &&
            micLangAfterPermission != null
        ) {
            startListening(micLangAfterPermission!!)
        } else if (requestCode == 1001) {
            status.text = getString(R.string.error, "нет разрешения на микрофон")
        }
        micLangAfterPermission = null
    }

    private fun startListening(lang: String) {
        if (!VoiceRepo.isDownloaded(this, lang)) {
            status.text = getString(R.string.downloading_voice)
            startVoiceDownload(lang)
            return
        }
        status.text = getString(R.string.voice_model_loading)
        Thread {
            try {
                voskModel = Model(VoiceRepo.modelDir(this, lang).absolutePath)
                val recognizer = Recognizer(voskModel, 16000.0f)
                speechService = SpeechService(recognizer, 16000.0f)
                speechService?.startListening(object : org.vosk.android.RecognitionListener {
                    override fun onPartialResult(hypothesis: String?) {
                        val text = JSONObject(hypothesis ?: "{}").optString("partial", "")
                        if (text.isNotBlank()) {
                            runOnUiThread { source.setText(text) }
                        }
                    }

                    override fun onResult(hypothesis: String?) {
                        // финальный ответ приходит и через onFinalResult
                    }

                    override fun onFinalResult(hypothesis: String?) {
                        val text = JSONObject(hypothesis ?: "{}").optString("text", "")
                        if (text.isNotBlank()) {
                            runOnUiThread {
                                source.setText(text)
                                stopListening()
                                translateSmart(text)
                            }
                        }
                    }

                    override fun onError(exception: Exception?) {
                        runOnUiThread {
                            status.text = getString(R.string.error, exception?.message)
                            stopListening()
                        }
                    }

                    override fun onTimeout() {
                        runOnUiThread { stopListening() }
                    }
                })
                listening = true
                runOnUiThread {
                    status.text = getString(R.string.listening)
                    micBtn.alpha = 0.4f
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status.text = getString(R.string.error, e.message)
                }
            }
        }.start()
    }

    private fun stopListening() {
        listening = false
        try {
            speechService?.stop()
            speechService = null
        } catch (_: Exception) {
        }
        micBtn.alpha = 1.0f
    }

    // ---------------- Перевод ----------------

    /** Автоопределение языка, если выбран сегмент «Авто». */
    private fun translateSmart(text: String) {
        if (directionGroup.checkedButtonId == R.id.btnAuto) {
            status.text = getString(R.string.translating)
            LanguageIdentification.getClient().identifyLanguage(text)
                .addOnSuccessListener { code ->
                    if (code == "ru") {
                        startTranslation(text, TranslateLanguage.RUSSIAN, TranslateLanguage.ENGLISH, "RU → EN")
                    } else {
                        val note = if (code == "und") " (язык не определён)" else ""
                        startTranslation(text, TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, "EN → RU$note")
                    }
                }
                .addOnFailureListener {
                    startTranslation(text, TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, "EN → RU")
                }
        } else if (directionGroup.checkedButtonId == R.id.btnRuEn) {
            startTranslation(text, TranslateLanguage.RUSSIAN, TranslateLanguage.ENGLISH, "RU → EN")
        } else {
            startTranslation(text, TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, "EN → RU")
        }
    }

    private fun startTranslation(text: String, src: String, dst: String, label: String) {
        ensureModels(src, dst) {
            translator?.close()
            val options = TranslatorOptions.Builder()
                .setSourceLanguage(src)
                .setTargetLanguage(dst)
                .build()
            translator = Translation.getClient(options)
            status.text = getString(R.string.translating)
            status.setTextColor(ContextCompat.getColor(this, R.color.text2))
            val btn = findViewById<Button>(R.id.translateBtn)
            btn.text = getString(R.string.working)
            translator!!.translate(text)
                .addOnSuccessListener { translated ->
                    output.text = translated
                    status.text = getString(R.string.done) + " • $label"
                    status.setTextColor(ContextCompat.getColor(this, R.color.green))
                    showVerdict(btn, getString(R.string.done_short), R.color.green)
                }
                .addOnFailureListener {
                    status.text = getString(R.string.error, it.message)
                    status.setTextColor(ContextCompat.getColor(this, R.color.red))
                    showVerdict(btn, getString(R.string.fail_short), R.color.red)
                }
        }
    }

    /** Кнопка со своим ходом: вердикт на самой кнопке, возврат через 1,5 с. */
    private fun showVerdict(btn: Button, label: String, colorRes: Int) {
        val accent = getColor(R.color.accent)
        val onAccent = getColor(R.color.on_accent)
        btn.text = label
        btn.setBackgroundColor(getColor(colorRes))
        btn.setTextColor(getColor(R.color.on_accent))
        handler.postDelayed({
            btn.text = getString(R.string.translate)
            btn.setBackgroundColor(accent)
            btn.setTextColor(onAccent)
            status.setTextColor(ContextCompat.getColor(this, R.color.text2))
        }, 1500)
    }

    /** Модели скачиваются один раз (нужен интернет), дальше перевод идёт офлайн. */
    private fun ensureModels(src: String, dst: String, onReady: () -> Unit) {
        val manager = RemoteModelManager.getInstance()
        manager.getDownloadedModels(TranslateRemoteModel::class.java)
            .addOnSuccessListener { downloaded ->
                val codes = downloaded.map { it.language }
                val needed = listOf(src, dst).distinct()
                val missing = needed.filter { it !in codes }
                if (missing.isEmpty()) {
                    onReady()
                } else {
                    status.text = getString(R.string.downloading_models)
                    var left = missing.size
                    val conditions = DownloadConditions.Builder().build()
                    for (lang in missing) {
                        val model = TranslateRemoteModel.Builder(lang).build()
                        manager.download(model, conditions)
                            .addOnSuccessListener {
                                left -= 1
                                if (left == 0) {
                                    status.text = getString(R.string.models_ready)
                                    onReady()
                                }
                            }
                            .addOnFailureListener {
                                status.text = getString(R.string.download_failed, it.message)
                            }
                    }
                }
            }
    }

    override fun onDestroy() {
        super.onDestroy()
        translator?.close()
        stopListening()
        try {
            voskModel?.close()
        } catch (_: Exception) {
        }
    }
}
