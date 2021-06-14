import json
import os

import boto3


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
