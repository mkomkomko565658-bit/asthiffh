import os
import shutil
import subprocess
import zipfile
import requests
import telebot
from telebot import types

# بياناتك الأساسية (المشرف أو الحساب الذي سترتبط به البوتات)
BOT_TOKEN = "8609910233:AAGkIqt6AmWoruePS0w4zJ6ruwifenzRpbA"
GITHUB_TOKEN = "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"
GITHUB_USERNAME = "mkomkomko565658-bit"

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message):
  markup = types.InlineKeyboardMarkup(row_width=1)
  btn_help = types.InlineKeyboardButton(
      "ℹ️ طريقة الاستخدام", callback_data="help_info"
  )
  markup.add(btn_help)

  bot.send_message(
      message.chat.id,
      "أهلاً بك! هذا البوت مخصص لرفع مشاريعكم بشكل مستقل وآمن. 🚀\nكل مستخدم"
      " سيمتلك مستودعاً خاصاً به على GitHub.\nأرسل ملف المشروع بصيغة `.zip`"
      " لنبدأ:",
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

  # التحقق من أن الملف بصيغة zip
  if not file_name.endswith(".zip"):
    bot.reply_to(message, "❌ خطأ: الرجاء إرسال ملف مضغوط بصيغة .zip فقط.")
    return

  # تحديد اسم مستودع خاص لكل مستخدم بناءً على الـ Chat ID الخاص به
  user_repo_name = f"project-user-{chat_id}"

  bot.reply_to(
      message,
      "⚙️ جاري تجهيز مستودعك الخاص على GitHub وتحميل الملفات...",
  )

  # 1. إنشاء المستودع تلقائياً للمستخدم عبر GitHub API (إذا لم يكن موجوداً مسبقاً)
  api_url = "https://api.github.com/user/repos"
  headers = {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }
  payload = {
      "name": user_repo_name,
      "description": f"Isolated auto-created project for Telegram user {chat_id}",
      "private": False,  # جعل المستودع عاماً لكي يتوافق مع خطط Render المجانية بسهولة
  }

  response = requests.post(api_url, json=payload, headers=headers)
  # إذا كان المستودع موجوداً مسبقاً، سيستجيب كود 422 وهذا طبيعي سنكمل عملية الرفع إليه

  downloaded_file = bot.download_file(file_info.file_path)

  # إنشاء مجلد مؤقت للعمليات
  local_dir = f"temp_workspace_{chat_id}"
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
    os.remove(zip_path)
  except Exception as e:
    bot.reply_to(message, f"❌ فشل فك الملف المضغوط: {str(e)}")
    shutil.rmtree(local_dir)
    return

  # تنفيذ أوامر Git والرفع للمستودع الخاص بالمستخدم
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

    # التحقق من وجود remote مسبقاً لتفادي الأخطاء
    subprocess.run(["git", "remote", "add", "origin", remote_url], capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], check=True)

    # الرفع الإجباري لتحديث المستودع الخاص بالمستخدم
    subprocess.run(
        ["git", "push", "-u", "origin", "main", "--force"], check=True
    )

    os.chdir("..")
    shutil.rmtree(local_dir)

    # زر يوجه المستخدم لمستودعه الخاص
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
  print("البوت مع عزل المستخدمين يعمل الآن...")
  bot.polling(none_stop=True)
