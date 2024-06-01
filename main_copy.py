import discord  # 引入 discord 模塊
import random  # 引入隨機數模塊
import asyncio  # 引入異步IO模塊
import logging  # 引入日誌模塊
import os  # 引入操作系統模塊
from dotenv import load_dotenv  # 從 dotenv 模塊引入 load_dotenv 函數
from asyncio import Semaphore, Queue  # 從 asyncio 模塊引入 Semaphore 和 Queue

load_dotenv()
TOKEN = os.getenv('USER_TOKEN')
REACTIONS = os.getenv('REACTIONS').split(',')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
MIN_DELAY = int(os.getenv('MIN_DELAY'))
MAX_DELAY = int(os.getenv('MAX_DELAY'))
# allowed_ids = list(map(int, os.getenv("ALLOWED_IDS").split(',')))  # 從環境變數獲取允許的頻道 ID 列表並轉為整數列表

client = discord.Client()
semaphore = Semaphore(5)
message_queue = Queue()

async def process_messages():
    while True:
        message = await message_queue.get()
        await add_reactions(message)
        message_queue.task_done()

async def add_reactions(message):
    async with semaphore:
        message_deleted = False
        for reaction in REACTIONS:
            if message_deleted:
                break
            try:
                await message.add_reaction(reaction)
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)
            except discord.errors.NotFound:
                logging.error("Message not found. Skipping reactions.")
                message_deleted = True
            except discord.errors.Forbidden:
                logging.error("Permissions error. Skipping reactions.")
                message_deleted = True
            except discord.errors.HTTPException:
                logging.warning("Rate limit or network error. Retrying after delay.")
                await asyncio.sleep(5)
                await message.add_reaction(reaction)
            except Exception as e:
                logging.exception(f"An unexpected error occurred while adding reaction: {e}")

async def check_all_messages(channel, user_id):
    async for message in channel.history(limit=2):  # limit=None 獲取所有訊息
        if message.author.id == user_id:
            try:
                await add_reactions(message)
                await asyncio.sleep(random.randint(MIN_DELAY, MAX_DELAY))  # 添加適當的延遲以避免速率限制
            except discord.errors.HTTPException as e:
                logging.warning(f"Rate limit or network error, waiting before retry: {e}")
                await asyncio.sleep(10)  # 遇到速率限制時等待更長時間
            except Exception as e:
                logging.exception(f"An unexpected error occurred: {e}")

            
async def shutdown_after_delay(delay):
    await asyncio.sleep(delay * 60)  # 延遲時間，delay 以分鐘為單位
    await client.close()
    print(f"Bot has been automatically shut down after {delay} minutes.")

@client.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID:
        await message_queue.put(message)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    user_id = int(input("Enter the user ID to check: "))
    mode = input("Enter '1' for checking and reacting to messages, '2' for original mode: ")
    channel = client.get_channel(CHANNEL_ID)
    if mode == '1':
        if channel:
            await check_all_messages(channel, user_id)
            print("Completed checking messages and adding reactions.")
            await client.close()  # 關閉 Discord 客戶端
            print("Bot has been shut down.")
        else:
            print("Channel not found. Check your any CHANNEL_ID.")
    elif mode == '2':
        print("Running original mode.")
        delay = int(input("Enter the number of minutes to run: "))
        asyncio.create_task(process_messages())
        asyncio.create_task(shutdown_after_delay(delay))

client.run(TOKEN)
