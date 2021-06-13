# bot.py
import asyncio
import json
import logging
import os

from discord.ext import commands, tasks
from web3.auto.infura import w3 as web3

UPDATE_INTERVAL_SECONDS = 300

logging.basicConfig(
    # filename="rewards_bots_log.txt",
    # filemode='a',
    # format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    # datefmt='%H:%M:%S',
    level=logging.INFO
)

bot = commands.Bot(command_prefix='/')
channel = bot.get_channel(os.getenv("DISCORD_CHANNEL_ID"))
logger = logging.getLogger("rewards-bot")

with open("./abis/BadgerTreeV2.json") as badger_tree_abi_file:
    badger_tree_abi = json.load(badger_tree_abi_file)

badger_tree_address = os.getenv("BADGER_TREE_ADDRESS")
contract = web3.eth.contract(
    address=web3.toChecksumAddress(badger_tree_address),
    abi=badger_tree_abi,
)

event_filter = contract.events.RootUpdated.createFilter(fromBlock="0x0")

def _parse_rewards_data(
    cycle,
    root, 
    contentHash, 
    startBlock, 
    endBlock, 
    timestamp, 
    blockNumber
):
    current_rewards_data = dict(
        cycle=cycle,
        root=web3.toHex(root),
        contentHash=web3.toHex(contentHash),
        startBlock=startBlock, 
        endBlock=endBlock, 
        timestamp=timestamp, 
        blockNumber=blockNumber
    )
    formatted_data = "\n".join(map(lambda x: f"{x[0]: <33} {x[1]}", current_rewards_data.items()))
    return f"```{formatted_data}```"


@bot.command(name="rewards")
async def rewards(ctx):
    global current_rewards_data
    await ctx.send(current_rewards_data)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} {bot.user.id}")


@tasks.loop(seconds=UPDATE_INTERVAL_SECONDS)
async def update_rewards():
    global current_rewards_data
    for event in event_filter.get_new_entries():
        current_rewards_data = _parse_rewards_data(*event["args"])
        await channel.send(current_rewards_data)


rewards_data = contract.functions.getCurrentMerkleData().call()
cycle = contract.functions.currentCycle().call()
current_rewards_data = _parse_rewards_data(cycle, *rewards_data)

update_rewards.start()
bot.run(os.getenv("BOT_TOKEN_REWARDS"))
