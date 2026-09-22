package ru.voodo.offlinetranslator

import android.content.Context
import android.os.Handler
import android.os.Looper
import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.zip.ZipInputStream

/** Голосовые модели Vosk: состояние, скачивание, распаковка. Офлайн после загрузки. */
object VoiceRepo {

    private val main = Handler(Looper.getMainLooper())

    private const val RU_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
    private const val EN_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    private const val RU_DIR = "vosk-model-small-ru-0.22"
    private const val EN_DIR = "vosk-model-small-en-us-0.15"

    fun modelDir(context: Context, lang: String): File =
        File(context.filesDir, if (lang == "ru") RU_DIR else EN_DIR)

    fun isDownloaded(context: Context, lang: String): Boolean {
        val dir = modelDir(context, lang)
        return File(dir, "conf/model.conf").exists() || File(dir, "am/final.mdl").exists()
    }

    fun download(context: Context, lang: String, onDone: () -> Unit, onFail: (String) -> Unit) {
        Thread {
            try {
                val url = URL(if (lang == "ru") RU_URL else EN_URL)
                val zip = File(context.cacheDir, "vosk-$lang.zip")
                val conn = url.openConnection() as HttpURLConnection
                conn.connectTimeout = 15000
                conn.readTimeout = 60000
                conn.inputStream.use { input ->
                    FileOutputStream(zip).use { output -> input.copyTo(output) }
                }
                unzip(zip, context.filesDir)
                zip.delete()
                // колбэки — строго в главный поток (UI трогают только там)
                main.post {
                    if (isDownloaded(context, lang)) onDone()
                    else onFail("файлы модели не найдены после распаковки")
                }
            } catch (e: Exception) {
                main.post { onFail(e.message ?: e.javaClass.simpleName) }
            }
        }.start()
    }

    private fun unzip(zip: File, target: File) {
        val outRoot = target.canonicalPath + File.separator
        ZipInputStream(BufferedInputStream(FileInputStream(zip))).use { zis ->
            var entry = zis.nextEntry
            while (entry != null) {
                val out = File(target, entry.name)
                if (!out.canonicalPath.startsWith(outRoot)) {
                    throw SecurityException("zip-slip: ${entry.name}")
                }
                if (entry.isDirectory) {
                    out.mkdirs()
                } else {
                    out.parentFile?.mkdirs()
                    FileOutputStream(out).use { zis.copyTo(it) }
                }
                entry = zis.nextEntry
            }
        }
    }
}
