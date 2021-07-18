# bot.py
import json
import logging
import os

from discord.ext import commands, tasks
from web3 import Web3

from utils import fetch_rewards_tree, formatter, summary

UPDATE_INTERVAL_SECONDS = 300
TEST = True if os.getenv("ENV") == "TEST" else False
WEB3_INFURA_HTTP_URL = os.getenv("WEB3_INFURA_HTTP_URL")

logging.basicConfig(
    level=logging.INFO
)

bot = commands.Bot(command_prefix="/")
logger = logging.getLogger("rewards-bot")
web3 = Web3(
    Web3.HTTPProvider(WEB3_INFURA_HTTP_URL)
)

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
    current_rewards_tree = fetch_rewards_tree(current_merkle_data, test=TEST)
    cache["reward_dist_summary"] = summary(current_rewards_tree)
    cache["formatted_data"] = formatter(
        {**current_merkle_data, **cache["reward_dist_summary"]}
    )


@bot.command(name="rewards")
async def rewards(ctx):
    formatted_data = cache["formatted_data"]
    await ctx.send(embed=formatted_data)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} {bot.user.id}")


@tasks.loop(seconds=UPDATE_INTERVAL_SECONDS)
async def update_rewards():
    cycle = contract.functions.currentCycle().call()
    if cache["current_merkle_data"]["cycle"] != cycle:
        rewards_data = contract.functions.getCurrentMerkleData().call()
        _parse_merkle_data(cycle, *rewards_data)
        logger.info(f"New merkle tree: {cache['current_merkle_data']}")

        formatted_data = cache["formatted_data"]
        channel = bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
        await channel.send(embed=formatted_data)


def start():
    rewards_data = contract.functions.getCurrentMerkleData().call()
    cycle = contract.functions.currentCycle().call()
    _parse_merkle_data(cycle, *rewards_data)

    update_rewards.start()
    bot.run(os.getenv("BOT_TOKEN_REWARDS"))


if __name__ == "__main__":
    start()
