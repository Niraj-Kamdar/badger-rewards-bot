# bot.py
import json
import logging
import os

from discord.ext import commands, tasks
from web3.auto.infura import w3 as web3

from utils import fetch_rewards_tree, formatter

UPDATE_INTERVAL_SECONDS = 300

logging.basicConfig(
    # filename="rewards_bots_log.txt",
    # filemode='a',
    # format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    # datefmt='%H:%M:%S',
    level=logging.INFO
)

bot = commands.Bot(command_prefix="/")
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
cache = {}


def _parse_merkle_data(
    cycle, root, contentHash, startBlock, endBlock, timestamp, blockNumber
):
    current_merkle_data = dict(
        cycle=cycle,
        root=web3.toHex(root),
        contentHash=web3.toHex(contentHash),
        startBlock=startBlock,
        endBlock=endBlock,
        timestamp=timestamp,
        blockNumber=blockNumber,
    )
    cache["current_merkle_data"] = current_merkle_data
    cache["formatted_merkle_data"] = formatter(current_merkle_data)
    cache["current_rewards_tree"] = fetch_rewards_tree(current_merkle_data, test=True)


@bot.command(name="rewards")
async def rewards(ctx):
    await ctx.send(cache["formatted_merkle_data"])


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} {bot.user.id}")


@tasks.loop(seconds=UPDATE_INTERVAL_SECONDS)
async def update_rewards():
    for event in event_filter.get_new_entries():
        _parse_merkle_data(*event["args"])
        await channel.send(cache["formatted_merkle_data"])


def start():
    rewards_data = contract.functions.getCurrentMerkleData().call()
    cycle = contract.functions.currentCycle().call()
    _parse_merkle_data(cycle, *rewards_data)

    update_rewards.start()
    bot.run(os.getenv("BOT_TOKEN_REWARDS"))


if __name__ == "__main__":
    start()
