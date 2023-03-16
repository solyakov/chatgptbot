# What is this?

This is a simple telegram bot for communicating with ChatGPT. It uses OpenAI API to generate responses to messages sent to it.

# How to use

To use this bot, you need to create a Telegram bot and get the API key. You can do this by talking to the BotFather on Telegram. Once you have the API key, you can set it in the `.env` file or as an environment variable. The key should be set as `TELEGRAM_BOT_TOKEN`.

You also need an OpenAI API key. You can get this by signing up for the OpenAI API. Once you have the key, you can set it in the `.env` file or as an environment variable. The key should be set as `OPENAI_API_KEY`.

# Running the bot

Use the following command to run the bot locally:

```bash
% make dev                                                                                                                                                                                     
python -m venv .venv                                            
.venv/bin/pip install --upgrade pip                          
...
```
