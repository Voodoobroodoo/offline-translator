package ru.voodo.offlinetranslator

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButtonToggleGroup
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.languageid.LanguageIdentification
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions

class MainActivity : AppCompatActivity() {

    private var translator: Translator? = null

    private lateinit var directionGroup: MaterialButtonToggleGroup
    private lateinit var source: EditText
    private lateinit var output: TextView
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        directionGroup = findViewById(R.id.directionGroup)
        source = findViewById(R.id.source)
        output = findViewById(R.id.output)
        status = findViewById(R.id.status)
        val translateBtn = findViewById<Button>(R.id.translateBtn)
        val copyBtn = findViewById<Button>(R.id.copyBtn)
        val swapBtn = findViewById<Button>(R.id.swapBtn)
        val modelsBtn = findViewById<Button>(R.id.modelsBtn)

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

        modelsBtn.setOnClickListener {
            downloadModels { status.text = getString(R.string.models_ready) }
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
                    // нет определения — переводим как английский
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
            translator!!.translate(text)
                .addOnSuccessListener { translated ->
                    output.text = translated
                    status.text = getString(R.string.done) + " • $label"
                }
                .addOnFailureListener {
                    status.text = getString(R.string.error, it.message)
                }
        }
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

    private fun downloadModels(onReady: () -> Unit) {
        status.text = getString(R.string.downloading_models)
        ensureModels(TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN, onReady)
    }

    override fun onDestroy() {
        super.onDestroy()
        translator?.close()
    }
}
