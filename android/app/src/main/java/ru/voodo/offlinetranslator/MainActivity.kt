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
import android.widget.ImageButton
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
    private lateinit var micBtn: ImageButton

    // Vosk
    private var voskModel: Model? = null
    private var speechService: SpeechService? = null
    private var listening = false
    private var micLangAfterPermission: String? = null
    private val transcript = StringBuilder()

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
                status.text = getString(R.string.stopped_hint)
                status.setTextColor(ContextCompat.getColor(this, R.color.text2))
            } else {
                startMicFlow()
            }
        }

        translateBtn.setOnClickListener {
            if (listening) stopListening()
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

        // В«РџРѕРґРµР»РёС‚СЊСЃСЏ в†’ РћС„Р»Р°Р№РЅ-РїРµСЂРµРІРѕРґС‡РёРєВ» РёР· РґСЂСѓРіРёС… РїСЂРёР»РѕР¶РµРЅРёР№
        val shared = intent?.takeIf { it.action == Intent.ACTION_SEND }?.getStringExtra(Intent.EXTRA_TEXT)
        if (!shared.isNullOrBlank()) {
            source.setText(shared)
            status.text = getString(R.string.shared_hint)
            translateSmart(shared)
        }

        // РЎРєСЂС‹С‚С‹Р№ СЃР°РјРѕС‚РµСЃС‚ РґРІРёР¶РєР°: am start --es wav_path /sdcard/test.wav --es wav_lang en
        intent?.getStringExtra("wav_path")?.let { path ->
            val lang = intent.getStringExtra("wav_lang") ?: "en"
            status.text = getString(R.string.voice_model_loading)
            ensureVoiceModel(lang) { recognizeWavFile(path, lang) }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshChips()
    }

    // ---------------- Р“РѕС‚РѕРІРЅРѕСЃС‚СЊ РєРѕРјРїРѕРЅРµРЅС‚РѕРІ ----------------

    private fun refreshChips() {
        // РўРµРєСЃС‚РѕРІС‹Рµ РјРѕРґРµР»Рё (ML Kit)
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

        // Р“РѕР»РѕСЃРѕРІС‹Рµ РјРѕРґРµР»Рё (Vosk)
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

    private fun ensureVoiceModel(lang: String, onReady: () -> Unit) {
        if (VoiceRepo.isDownloaded(this, lang)) {
            onReady()
            return
        }
        status.text = getString(R.string.downloading_voice)
        VoiceRepo.download(this, lang, { refreshChips(); onReady() }, { err ->
            status.text = getString(R.string.error, err)
            status.setTextColor(ContextCompat.getColor(this, R.color.red))
        })
    }

    /** РЎР°РјРѕС‚РµСЃС‚ РґРІРёР¶РєР°: СЂР°СЃРїРѕР·РЅР°РІР°РЅРёРµ РёР· WAV-С„Р°Р№Р»Р° (16 РєР“С†, 16 Р±РёС‚, РјРѕРЅРѕ). */
    private fun recognizeWavFile(path: String, lang: String) {
        Thread {
            try {
                val model = Model(VoiceRepo.modelDir(this, lang).absolutePath)
                val recognizer = Recognizer(model, 16000.0f)
                val raw = java.io.File(path).readBytes()
                val shorts = ShortArray((raw.size - 44) / 2)
                for (i in shorts.indices) {
                    val lo = raw[44 + i * 2].toInt() and 0xFF
                    val hi = raw[45 + i * 2].toInt()
                    shorts[i] = ((hi shl 8) or lo).toShort()
                }
                var i = 0
                while (i + 4096 <= shorts.size) {
                    recognizer.acceptWaveForm(shorts.copyOfRange(i, i + 4096), 4096)
                    i += 4096
                }
                if (i < shorts.size) {
                    recognizer.acceptWaveForm(shorts.copyOfRange(i, shorts.size), shorts.size - i)
                }
                val text = JSONObject(recognizer.result).optString("text", "")
                runOnUiThread {
                    source.setText(text)
                    if (text.isNotBlank()) {
                        translateSmart(text)
                    } else {
                        status.text = "WAV: РїСѓСЃС‚РѕР№ СЂРµР·СѓР»СЊС‚Р°С‚"
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status.text = getString(R.string.error, e.message)
                    status.setTextColor(ContextCompat.getColor(this, R.color.red))
                }
            }
        }.start()
    }

    private fun downloadModels(onReady: () -> Unit) {
        status.text = getString(R.string.downloading_text)
        downloadTextModels(onReady)
    }

    // ---------------- РњРёРєСЂРѕС„РѕРЅ Рё Vosk ----------------

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
            status.text = getString(R.string.error, "РЅРµС‚ СЂР°Р·СЂРµС€РµРЅРёСЏ РЅР° РјРёРєСЂРѕС„РѕРЅ")
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
        // РЎРµСЃСЃРёСЏ РґРёРєС‚РѕРІРєРё: РЅР°РєРѕРїР»РµРЅРЅС‹Р№ С‚РµРєСЃС‚ СЃС‚Р°СЂС‚СѓРµС‚ СЃ С‚РѕРіРѕ, С‡С‚Рѕ СѓР¶Рµ РІ РїРѕР»Рµ
        transcript.setLength(0)
        transcript.append(source.text.toString())
        Thread {
            try {
                val model = VoiceRepo.getModel(this, lang)
                val recognizer = Recognizer(model, 16000.0f)
                speechService = SpeechService(recognizer, 16000.0f)
                speechService?.startListening(object : org.vosk.android.RecognitionListener {
                    override fun onPartialResult(hypothesis: String?) {
                        val partial = JSONObject(hypothesis ?: "{}").optString("partial", "")
                        if (partial.isNotBlank()) {
                            runOnUiThread { source.setText(displayWithPartial(partial)) }
                        }
                    }

                    override fun onResult(hypothesis: String?) {
                        // С„РёРЅР°Р»СЊРЅС‹Р№ РѕС‚РІРµС‚ РїСЂРёС…РѕРґРёС‚ Рё С‡РµСЂРµР· onFinalResult
                    }

                    override fun onFinalResult(hypothesis: String?) {
                        val utterance = JSONObject(hypothesis ?: "{}").optString("text", "")
                        runOnUiThread {
                            // РџР°СѓР·Р° = РєРѕРЅРµС† С„СЂР°Р·С‹: СЃР»РёРІР°РµРј СЃ РЅР°РєРѕРїР»РµРЅРЅС‹Рј Рё РїСЂРѕРґРѕР»Р¶Р°РµРј СЃР»СѓС€Р°С‚СЊ
                            if (utterance.isNotBlank()) {
                                transcript.setLength(0)
                                transcript.append(mergeTranscript(utterance))
                                source.setText(transcript.toString())
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
        status.setTextColor(ContextCompat.getColor(this, R.color.text2))
    }

    /** РЎР»РёСЏРЅРёРµ: РµСЃР»Рё Vosk РїСЂРёСЃР»Р°Р» С‚РµРєСЃС‚ С†РµР»РёРєРѕРј (СЃ РєРѕРЅС‚РµРєСЃС‚РѕРј) вЂ” Р·Р°РјРµРЅСЏРµРј, РёРЅР°С‡Рµ РґРѕРїРёСЃС‹РІР°РµРј. */
    private fun mergeTranscript(incoming: String): String {
        val base = transcript.toString().trim()
        val inc = incoming.trim()
        return when {
            inc.isEmpty() -> base
            base.isEmpty() -> inc
            inc.startsWith(base) -> inc
            inc.contains(base) -> inc
            else -> "$base $inc"
        }
    }

    /** РћС‚РѕР±СЂР°Р¶РµРЅРёРµ С‡Р°СЃС‚РёС‡РЅРѕРіРѕ СЂРµР·СѓР»СЊС‚Р°С‚Р° РїРѕРІРµСЂС… РЅР°РєРѕРїР»РµРЅРЅРѕРіРѕ. */
    private fun displayWithPartial(partial: String): String {
        val base = transcript.toString().trim()
        val p = partial.trim()
        return when {
            p.isEmpty() -> base
            base.isEmpty() -> p
            p.startsWith(base) -> p
            p.contains(base) -> p
            else -> "$base $p"
        }
    }

    // ---------------- РџРµСЂРµРІРѕРґ ----------------

    /** РђРІС‚РѕРѕРїСЂРµРґРµР»РµРЅРёРµ СЏР·С‹РєР°, РµСЃР»Рё РІС‹Р±СЂР°РЅ СЃРµРіРјРµРЅС‚ В«РђРІС‚РѕВ». */
    private fun translateSmart(text: String) {
        if (directionGroup.checkedButtonId == R.id.btnAuto) {
            status.text = getString(R.string.translating)
            LanguageIdentification.getClient().identifyLanguage(text)
                .addOnSuccessListener { code ->
                    if (code == "ru") {
                        startTranslation(text, TranslateLanguage.RUSSIAN, TranslateLanguage.ENGLISH, "RU в†’ EN")
                    } else {
                        val note = if (code == "und") " (СЏР·С‹Рє РЅРµ РѕРїСЂРµРґРµР»С‘РЅ)" else ""
                        startTranslation(text, TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, "EN в†’ RU$note")
                    }
                }
                .addOnFailureListener {
                    startTranslation(text, TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, "EN в†’ RU")
                }
        } else if (directionGroup.checkedButtonId == R.id.btnRuEn) {
            startTranslation(text, TranslateLanguage.RUSSIAN, TranslateLanguage.ENGLISH, "RU в†’ EN")
        } else {
            startTranslation(text, TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, "EN в†’ RU")
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
                    status.text = getString(R.string.done) + " вЂў $label"
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

    /** РљРЅРѕРїРєР° СЃРѕ СЃРІРѕРёРј С…РѕРґРѕРј: РІРµСЂРґРёРєС‚ РЅР° СЃР°РјРѕР№ РєРЅРѕРїРєРµ, РІРѕР·РІСЂР°С‚ С‡РµСЂРµР· 1,5 СЃ. */
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

    /** РњРѕРґРµР»Рё СЃРєР°С‡РёРІР°СЋС‚СЃСЏ РѕРґРёРЅ СЂР°Р· (РЅСѓР¶РµРЅ РёРЅС‚РµСЂРЅРµС‚), РґР°Р»СЊС€Рµ РїРµСЂРµРІРѕРґ РёРґС‘С‚ РѕС„Р»Р°Р№РЅ. */
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

