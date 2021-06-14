import json
import os
from decimal import Decimal, getcontext
from statistics import mean, median

import boto3

getcontext().prec = 28


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
    # TODO Files should be hashed and signed by keeper to prevent tampering
    # TODO How will we upload addresses securely?
    # We will check signature before posting
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
    token_dist_data = {
        key: list(
            map(
                lambda x: x["totals"]["0x3472A5A71965499acd81997a54BBA8D852C6E53d"],
                val.values(),
            )
        )
        for key, val in rewards_tree["userData"].items()
        if "digg" not in key.lower()
    }

    return {key: _list_summary(val) for key, val in token_dist_data.items()}


def _list_summary(array):
    count = len(array)
    array = list(map(lambda x: Decimal(x) / Decimal(10 ** 18), array))
    return dict(
        max=str(max(array)),
        min=str(min(array)),
        mean=str(mean(array)),
        sum=str(sum(array)),
        median=str(median(array)),
        count=count,
    )
