import os
import shutil
import subprocess
import threading
import zipfile
from flask import Flask
import requests
import telebot
from telebot import types

# بيانات البوت وحسابك
BOT_TOKEN = "8609910233:AAGkIqt6AmWoruePS0w4zJ6ruwifenzRpbA"
GITHUB_TOKEN = "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"
GITHUB_USERNAME = "mkomkomko565658-bit"

bot = telebot.TeleBot(BOT_TOKEN)

# سرفر ويب مصغر لكي يتوافق مع شروط استضافة Render وتظل الخدمة تعمل
app = Flask(__name__)


@app.route("/")
def home():
  return "Telegram Deploy Bot is active and running 24/7! 🚀"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# --- دوال البوت ---
@bot.message_handler(commands=["start"])
def send_welcome(message):
  markup = types.InlineKeyboardMarkup(row_width=1)
  btn_help = types.InlineKeyboardButton(
      "ℹ️ طريقة الاستخدام", callback_data="help_info"
  )
  markup.add(btn_help)

  bot.send_message(
      message.chat.id,
      "أهلاً بك! هذا البوت مخصص لرفع مشاريعكم بشكل مستقل وآمن على Render. 🚀\nكل"
      " مستخدم سيمتلك مستودعاً خاصاً به على GitHub.\nأرسل ملف المشروع بصيغة"
      " `.zip` لنبدأ:",
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data == "help_info")
def callback_help(call):
  bot.answer_callback_query(call.id)
  bot.send_message(
      call.message.chat.id,
      "📌 **دليل الاستخدام:**\n1. أرسل ملف مشروعك مضغوطاً بصيغة"
      " `.zip`.\n2. سيقوم البوت بإنشاء مستودع خاص بك تلقائياً ورفع الملفات"
      " إليه.\n3. يمكنك بعدها ربط مستودعك الخاص بموقع Render للنشر.",
      parse_mode="Markdown",
  )


@bot.message_handler(content_types=["document"])
def handle_docs(message):
  chat_id = message.chat.id
  file_info = bot.get_file(message.document.file_id)
  file_name = message.document.file_name

  if not file_name.endswith(".zip"):
    bot.reply_to(message, "❌ خطأ: الرجاء إرسال ملف مضغوط بصيغة .zip فقط.")
    return

  user_repo_name = f"project-user-{chat_id}"
  bot.reply_to(
      message,
      "⚙️ جاري تجهيز مستودعك الخاص على GitHub وتحميل الملفات...",
  )

  api_url = "https://api.github.com/user/repos"
  headers = {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }
  payload = {
      "name": user_repo_name,
      "description": f"Isolated auto-created project for Telegram user {chat_id}",
      "private": False,
  }

  requests.post(api_url, json=payload, headers=headers)

  downloaded_file = bot.download_file(file_info.file_path)
  local_dir = f"temp_workspace_{chat_id}"
  if os.path.exists(local_dir):
    shutil.rmtree(local_dir)
  os.makedirs(local_dir)

  zip_path = os.path.join(local_dir, "project.zip")
  with open(zip_path, "wb") as new_file:
    new_file.write(downloaded_file)

  try:
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
      zip_ref.extractall(local_dir)
    os.remove(zip_path)
  except Exception as e:
    bot.reply_to(message, f"❌ فشل فك الملف المضغوط: {str(e)}")
    shutil.rmtree(local_dir)
    return

  try:
    os.chdir(local_dir)

    subprocess.run(["git", "init"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "bot@shadowcod.com"], check=True
    )
    subprocess.run(["git", "config", "user.name", "DeployBot"], check=True)

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "-m", "Auto-deploy via Telegram Bot"], check=True
    )

    remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{user_repo_name}.git"
    subprocess.run(["git", "remote", "add", "origin", remote_url], capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], check=True)
    subprocess.run(
        ["git", "push", "-u", "origin", "main", "--force"], check=True
    )

    os.chdir("..")
    shutil.rmtree(local_dir)

    markup = types.InlineKeyboardMarkup()
    btn_repo = types.InlineKeyboardButton(
        "🔗 عرض مستودعك الخاص على GitHub",
        url=f"https://github.com/{GITHUB_USERNAME}/{user_repo_name}",
    )
    markup.add(btn_repo)

    bot.send_message(
        chat_id,
        f"✅ **تم إنشاء مستودعك الخاص ورفع المشروع بنجاح!**\n📂 اسم المستودع:"
        f" `{user_repo_name}`\n🔥 يمكنك الآن ربطه بموقع Render لنشر"
        " سيرفرك.",
        parse_mode="Markdown",
        reply_markup=markup,
    )

  except subprocess.CalledProcessError as e:
    os.chdir("..")
    if os.path.exists(local_dir):
      shutil.rmtree(local_dir)
    bot.reply_to(
        message, f"❌ حدث خطأ أثناء رفع الكود:\n`{str(e)}`", parse_mode="Markdown"
    )
  except Exception as e:
    os.chdir("..")
    if os.path.exists(local_dir):
      shutil.rmtree(local_dir)
    bot.reply_to(message, f"❌ حدث خطأ غير متوقع:\n{str(e)}")


if __name__ == "__main__":
  # تشغيل سيرفر الفلاسك في مسار خلفي لكي يعمل Render بشكل صحيح
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.start()

  print("البوت وسرفر الويب يعملان الآن بالتوازي...")
  bot.infinity_polling()
