from dataclasses import dataclass
import os
import sys
import time
from typing import Literal, TypeAlias, TypedDict

import openai
import telegram
from dotenv import find_dotenv, load_dotenv
from telegram import BotCommand, Update, constants
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
)


class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class Settings:
    model: Literal["gpt-3.5-turbo", "gpt-4"]


@dataclass
class Chat:
    messages: list[Message]
    settings: Settings


load_dotenv(find_dotenv())

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_TELEGRAM_USER_IDS = set(
    map(int, os.getenv("ALLOWED_TELEGRAM_USER_IDS").split(","))
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1200))
HISTORY_SIZE_LIMIT = int(os.getenv("HISTORY_SIZE_LIMIT", 10))
N_CHOICES = int(os.getenv("N_CHOICES", 1))
TEMPERATURE = float(os.getenv("TEMPERATURE", 1.0))
PRESENCE_PENALTY = float(os.getenv("PRESENCE_PENALTY", 0.0))
FREQUENCY_PENALTY = float(os.getenv("FREQUENCY_PENALTY", 0.0))
TELEGRAM_CHUNK_SIZE_LIMIT = int(os.getenv("TELEGRAM_CHUNK_SIZE_LIMIT", 4096))
MAX_RETRIES = 3
INIT_MESSAGE = Message(role="system", content="You are a helpful assistant.")

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

openai.api_key = OPENAI_API_KEY

chat_id_type: TypeAlias = int
chats: dict[chat_id_type, Chat] = dict()


async def summarise(chat: Chat) -> str:
    """
    Summarises the conversation history.
    """
    SUMMARIZE_TEMPERATURE = 0.4
    for i in range(MAX_RETRIES):
        try:
            response = await openai.ChatCompletion.acreate(
                model=chat.settings.model,
                messages=[
                    Message(
                        role="assistant",
                        content="Summarize this conversation in 700 characters or less, using the main language of the conversation.",
                    ),
                    Message(role="user", content=str(chat.messages)),
                ],
                temperature=SUMMARIZE_TEMPERATURE,
            )
            return response.choices[0]["message"]["content"]
        except Exception as e:
            print(e, file=sys.stderr)
            if i == MAX_RETRIES - 1:
                raise RuntimeError("Failed to summarise the conversation.") from e
            time.sleep(i)


async def remember(chat: Chat, message: Message) -> None:
    """
    Adds a message to the conversation history.
    """
    if len(chat.messages) > HISTORY_SIZE_LIMIT:
        try:
            summary = await summarise(chat)
        except Exception as e:
            print(e, file=sys.stderr)
        else:
            chat.messages = [
                INIT_MESSAGE,
                Message(role="assistant", content=summary),
            ]
    chat.messages.append(message)


async def error_handler(_update: Update, context: CallbackContext) -> None:
    """
    Handles errors in the telegram-python-bot library.
    """
    print(context.error, file=sys.stderr)


async def reply(update: Update, context: CallbackContext) -> None:
    """
    Gets a response from the GPT model.
    """
    if update.message.from_user.id not in ALLOWED_TELEGRAM_USER_IDS:
        print(f"Unknown user id: {update.message.from_user.id}", file=sys.stderr)
        return

    if (chat_id := update.effective_chat.id) not in chats:
        chats[chat_id] = Chat(
            messages=[INIT_MESSAGE],
            settings=Settings(model=OPENAI_MODEL),
        )

    chat = chats[chat_id]

    await remember(chat, Message(role="user", content=update.message.text))

    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.TYPING
    )
    for i in range(MAX_RETRIES):
        try:
            response = await openai.ChatCompletion.acreate(
                model=chat.settings.model,
                messages=chat.messages,
                temperature=TEMPERATURE,
                n=N_CHOICES,
                max_tokens=MAX_TOKENS,
                presence_penalty=PRESENCE_PENALTY,
                frequency_penalty=FREQUENCY_PENALTY,
            )
            break
        except Exception as e:
            print(e, file=sys.stderr)
            if i == MAX_RETRIES - 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже. Ошибка: {str(e)}",
                )
                return
            time.sleep(i)

    answer = response.choices[0]["message"]["content"].strip()

    await remember(chat, Message(role="assistant", content=answer))

    for i in range(0, len(answer), TELEGRAM_CHUNK_SIZE_LIMIT):
        chunk = answer[i : i + TELEGRAM_CHUNK_SIZE_LIMIT]
        await context.bot.send_message(
            chat_id=chat_id, text=chunk, parse_mode=constants.ParseMode.MARKDOWN
        )


async def post_init(application: Application) -> None:
    """
    Post initialization hook for the bot.
    """
    await application.bot.set_my_commands(
        [
            BotCommand(
                command="model",
                description=f"Устанавливает модель GPT (например, /model <gpt-4|gpt-3.5-turbo|...> ). По умолчанию это {OPENAI_MODEL}.",
            ),
            BotCommand(command="reset", description="Перезагружает разговор."),
        ]
    )
    print("Ready 🚀")


async def handle_model(update: Update, context: CallbackContext):
    if (chat_id := update.effective_chat.id) not in chats:
        return
    chat = chats[chat_id]
    model = update.message.text.replace("/model", "").strip() or OPENAI_MODEL
    chat.settings.model = model
    await context.bot.send_message(chat_id=chat_id, text=f"Использую модель {model}.")


async def handle_reset(update: Update, context: CallbackContext):
    if (chat_id := update.effective_chat.id) not in chats:
        return
    chat = chats[chat_id]
    chat.messages = [INIT_MESSAGE]
    await context.bot.send_message(chat_id=chat_id, text="Разговор перезагрузился.")


def main():
    application = (
        ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )
    application.add_handler(CommandHandler("model", handle_model))
    application.add_handler(CommandHandler("reset", handle_reset))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply))
    application.add_error_handler(error_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
