package ru.voodo.offlinetranslator

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions

class MainActivity : AppCompatActivity() {

    private var translator: Translator? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val direction = findViewById<Spinner>(R.id.direction)
        val source = findViewById<EditText>(R.id.source)
        val output = findViewById<TextView>(R.id.output)
        val status = findViewById<TextView>(R.id.status)
        val translateBtn = findViewById<Button>(R.id.translateBtn)
        val copyBtn = findViewById<Button>(R.id.copyBtn)
        val modelsBtn = findViewById<Button>(R.id.modelsBtn)

        fun currentTranslator(): Translator {
            val (src, dst) = if (direction.selectedItemPosition == 0)
                TranslateLanguage.ENGLISH to TranslateLanguage.RUSSIAN
            else
                TranslateLanguage.RUSSIAN to TranslateLanguage.ENGLISH
            val options = TranslatorOptions.Builder()
                .setSourceLanguage(src)
                .setTargetLanguage(dst)
                .build()
            return Translation.getClient(options)
        }

        // Модели скачиваются один раз (нужен интернет), дальше перевод идёт офлайн
        fun ensureModels(onReady: () -> Unit) {
            val manager = RemoteModelManager.getInstance()
            manager.getDownloadedModels(TranslateRemoteModel::class.java)
                .addOnSuccessListener { downloaded ->
                    val codes = downloaded.map { it.language }
                    val needed = if (direction.selectedItemPosition == 0)
                        listOf(TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN)
                    else
                        listOf(TranslateLanguage.RUSSIAN, TranslateLanguage.ENGLISH)
                    val missing = needed.filter { it !in codes }
                    if (missing.isEmpty()) {
                        onReady()
                    } else {
                        status.text = getString(R.string.downloading_models)
                        var left = missing.size
                        for (lang in missing) {
                            val model = TranslateRemoteModel.Builder(lang).build()
                            manager.download(model)
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

        modelsBtn.setOnClickListener {
            translator?.close()
            translator = null
            ensureModels { status.text = getString(R.string.models_ready) }
        }

        translateBtn.setOnClickListener {
            val text = source.text.toString().trim()
            if (text.isEmpty()) {
                status.text = getString(R.string.empty_input)
                return@setOnClickListener
            }
            ensureModels {
                translator?.close()
                translator = currentTranslator()
                status.text = getString(R.string.translating)
                translator!!.translate(text)
                    .addOnSuccessListener { translated ->
                        output.text = translated
                        status.text = getString(R.string.done)
                    }
                    .addOnFailureListener {
                        status.text = getString(R.string.error, it.message)
                    }
            }
        }

        copyBtn.setOnClickListener {
            val text = output.text.toString()
            if (text.isNotBlank()) {
                val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("translation", text))
                Toast.makeText(this, R.string.copied, Toast.LENGTH_SHORT).show()
            }
        }

        status.text = getString(R.string.hint_models)
    }

    override fun onDestroy() {
        super.onDestroy()
        translator?.close()
    }
}
