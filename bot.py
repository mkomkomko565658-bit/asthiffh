import os
import shutil
import subprocess
import zipfile
import telebot

# ضع بياناتك هنا
BOT_TOKEN = "أدخل_توكن_البوت_من_BotFather"
GITHUB_TOKEN = "أدخل_توكن_جيت_هب_الخاص_بك"
GITHUB_USERNAME = "mkomkomko565658-bit"
REPO_NAME = "asthiffh"

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "أهلاً بك! أرسل ملف المشروع بصيغة (.zip) وسأقوم برفعه إلى GitHub وتحديث"
      " السيرفر تلقائياً على Render. 🚀",
  )


@bot.message_handler(content_types=["document"])
def handle_docs(message):
  file_info = bot.get_file(message.document.file_id)
  file_name = message.document.file_name

  # التحقق من أن الملف بصيغة zip
  if not file_name.endswith(".zip"):
    bot.reply_to(message, "❌ خطأ: الرجاء إرسال ملف مضغوط بصيغة .zip فقط.")
    return

  bot.reply_to(
      message, "📥 جاري تحميل الملف، فك الضغط، والرفع إلى GitHub..."
  )

  downloaded_file = bot.download_file(file_info.file_path)

  # إنشاء مجلد مؤقت للعمليات
  local_dir = "temp_project_workspace"
  if os.path.exists(local_dir):
    shutil.rmtree(local_dir)
  os.makedirs(local_dir)

  zip_path = os.path.join(local_dir, "project.zip")
  with open(zip_path, "wb") as new_file:
    new_file.write(downloaded_file)

  # فك ملف الـ zip
  try:
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
      zip_ref.extractall(local_dir)
    os.remove(zip_path)  # حذف ملف الـ zip الأصلي بعد الفك
  except Exception as e:
    bot.reply_to(message, f"❌ فشل فك الملف المضغوط: {str(e)}")
    shutil.rmtree(local_dir)
    return

  # تنفيذ أوامر Git والرفع
  try:
    os.chdir(local_dir)

    # إعدادات Git الأولية
    subprocess.run(["git", "init"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "bot@shadowcod.com"], check=True
    )
    subprocess.run(["git", "config", "user.name", "DeployBot"], check=True)

    # إضافة الملفات وعمل Commit
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "-m", "Auto-deploy via Telegram Bot"], check=True
    )

    # ربط المستودع عن بُعد باستخدام التوكن
    remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git"
    subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
    subprocess.run(["git", "branch", "-M", "main"], check=True)

    # الرفع الإجباري لتحديث السيرفر مباشرة
    subprocess.run(
        ["git", "push", "-u", "origin", "main", "--force"], check=True
    )

    # العودة للمسار الرئيسي وحذف المجلد المؤقت
    os.chdir("..")
    shutil.rmtree(local_dir)

    bot.reply_to(
        message,
        "✅ تم رفع المشروع وتحديثه على GitHub بنجاح!\n🔥 سيقوم Render الآن بإعادة"
        " بناء ونشر التحديث تلقائياً.",
    )

  except subprocess.CalledProcessError as e:
    os.chdir("..")
    if os.path.exists(local_dir):
      shutil.rmtree(local_dir)
    bot.reply_to(
        message, f"❌ حدث خطأ أثناء تنفيذ أوامر Git:\n`{str(e)}`", parse_mode="Markdown"
    )
  except Exception as e:
    os.chdir("..")
    if os.path.exists(local_dir):
      shutil.rmtree(local_dir)
    bot.reply_to(message, f"❌ حدث خطأ غير متوقع:\n{str(e)}")


if __name__ == "__main__":
  print("البوت يعمل الآن ويستمع للملفات...")
  bot.polling(none_stop=True)
