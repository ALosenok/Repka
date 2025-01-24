#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from Route_Perfect_pipe import pipeline_flow
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler


# In[ ]:


nest_asyncio.apply()
executor = ThreadPoolExecutor()

START = 0


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('What city would you like to visit and for how long?')
    return START

async def handle_input(update: Update, context: CallbackContext) -> int:
    input_text = update.message.text
    await update.message.reply_text("Route generation is in process...")
    
    messages = pipeline_flow(input_text)
    try:
        for msg in messages:
            print(f"Sending: {msg}")
            await update.message.reply_text(msg)
            await asyncio.sleep(1)
    
        await update.message.reply_text("The route is done. You can start a new conversation with /start")

    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("An error occurred. Please try again later with /start.")
        conn.rollback()
    # End the conversation
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Handle cancel command."""
    await update.message.reply_text("Conversation ended. You can start a new one anytime.")
    return ConversationHandler.END

# Main function to run the bot
def main():
    bot_token = '******************************' 
    application = Application.builder().token(bot_token).build()

    conversation_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
            states={
                START: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )


    application.add_handler(conversation_handler)

    application.run_polling()

if __name__ == '__main__':
    main()

