import json
import os
from collections import Counter, defaultdict

import boto3
from pycoingecko import CoinGeckoAPI

from cgMapping import cgMapping

cg = CoinGeckoAPI()


def download_tree(fileName, test=False):
    if test:
        with open("data/rewards.json") as f:
            rewards = json.load(f)
        return rewards

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    s3_clientobj = s3.get_object(Bucket=upload_bucket, Key=upload_file_key)
    s3_clientdata = s3_clientobj["Body"].read().decode("utf-8")

    return json.loads(s3_clientdata)


def fetch_rewards_tree(merkle, test=False):
    pastFile = f"rewards-1-{merkle['contentHash']}.json"

    currentTree = download_tree(pastFile, test)

    if not test:
        assert currentTree["merkleRoot"] == merkle["root"]

        lastUpdateOnChain = merkle["blockNumber"]
        lastUpdate = int(currentTree["endBlock"])

        # Ensure file tracks block within 1 day of upload
        assert abs(lastUpdate - lastUpdateOnChain) < 6500

        # Ensure upload was after file tracked
        assert lastUpdateOnChain >= lastUpdate

    return currentTree


def formatter(merkle_data):
    formatted_data = "\n".join(
        map(lambda x: f"{x[0]: <33} {x[1]}", merkle_data.items())
    )
    return f"```{formatted_data}```"


def summary(rewards_tree):
    token_dist_data = defaultdict(lambda: defaultdict(list))
    summary = defaultdict(Counter)
    for sett, settDist in rewards_tree["userData"].items():
        for userDist in settDist.values():
            for token in userDist["totals"]:
                # Todo: add support for digg rewards
                # Need to fetch actual reward in digg from the share
                if token != "0x798D1bE841a82a273720CE31c822C61a67a601C3":
                    token_dist_data[sett][token].append(userDist["totals"][token])

    for sett, value in token_dist_data.items():
        for token in value:
            summary[cgMapping[token]["name"]] += _list_summary(
                token_dist_data[sett][token],
                cgMapping[token]["id"],
                cgMapping[token]["decimals"],
            )

    for token in summary:
        summary[token]["mean"] = summary[token]["sum"] / summary[token]["count"]
        summary[token]["mean(usd)"] = (
            summary[token]["sum(usd)"] / summary[token]["count"]
        )
    return summary


def _list_summary(array, cgTokenId, decimals):
    array = list(map(lambda x: x / 10 ** decimals, array))
    tokenPrice = cg.get_price(ids=cgTokenId, vs_currencies="usd")
    usdPrice = tokenPrice[cgTokenId]["usd"]
    summary = {
        "count": len(array),
        "sum": sum(array),
    }
    summary["sum(usd)"] = summary["sum"] * usdPrice
    # summary["mean"] = (summary["sum"] / summary["count"],)
    # summary["mean(usd)"] = (summary["sum(usd)"] / summary["count"],)
    return Counter(summary)


def _total_summary():
    pass
