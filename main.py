from datetime import datetime
import logging
import re
import sys
from atproto import Client, IdResolver
from time import sleep

import os
import requests
from atproto_client.models.app.bsky.feed.defs import FeedViewPost, PostView
from atproto_client.models.app.bsky.feed.get_feed import Params
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Setup Logging
logger = logging.getLogger(__name__)
stdout = logging.StreamHandler(stream=sys.stdout)
stdout.setLevel(logging.INFO)
logger.addHandler(stdout)
logger.setLevel(logging.INFO)
warning = logger.warning
info = logger.info

LAST_SENT_AT_FILENAME = "last_sent_at.txt"

USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if USERNAME == "": raise ValueError("Username is missing")
if PASSWORD == "": raise ValueError("Password is missing")
if WEBHOOK_URL == "": warning("Webhook Url is missing")

'''How frequently we check for new posts, in minutes'''
TIMEOUT = 5

'''How many seconds there should be between discord posts'''
DISCORD_TIMEOUT = 2


class Post:
    def __init__(self, post: FeedViewPost) -> None:
        self.author = post.post.author
        self.author_handle = post.post.author.handle
        self.author_display_name = post.post.author.display_name
        self.author_avatar = post.post.author.avatar
        self.author_profile_url = "https://bsky.app/profile/" + self.author_handle
        self.content = post.post.record.text
        self.embeds = post.post.record.embed
        self.url = atUriToBskyAppUrl(post.post.uri, author_handle=self.author_handle)
        self.time: datetime = datetime.fromisoformat(post.post.indexed_at)

    def __format__(self, format_spec: str, /) -> str:
        return f"""<Post by '@{self.author_handle}' at [{self.time.isoformat()}] \
url: [{self.url}]
with {"no" if self.embeds is None else ""} embeds:
    {self.content}>"""


def update_last_sent(time: datetime):
    logger.debug(f"Updating to {time.timestamp()}")
    with open(LAST_SENT_AT_FILENAME, 'w') as f:
        f.write(f"last_sent_at={time.timestamp()}")


def read_last_sent():
    timestamp = 0
    if os.path.exists(LAST_SENT_AT_FILENAME):
        with open(LAST_SENT_AT_FILENAME, 'r') as f:
            timestamp = f.read().split(sep='=')[1]
    return datetime.fromtimestamp(float(timestamp))


def fetch_new_user_posts(client: Client, user_did: str) -> list[Post]:
    next_page = None
    posts: list[Post] = []
    while True:
        data = client.get_author_feed(
            actor=user_did,
            cursor=next_page,
            filter='posts_and_author_threads',
            limit=30,
        )
        # For paging
        feed = data.feed
        next_page = data.cursor
        info(f"Requesting next page with cursor {next_page}")
        last_sent_at = read_last_sent()

        posts += map(lambda x: Post(x), feed)

        # Stop if the last post we collected is already older than since we last checked
        # Or if we are at the end of the timeline ;)
        if next_page is None or posts[-1].time.timestamp() < last_sent_at.timestamp():
            break
        # Prevent being rate limited
        sleep(0.5)

    def keep_post(p: Post):
        keep = p.time.timestamp() > last_sent_at.timestamp()
        if not keep: info(f"Skipping post from {p.time.isoformat()} @{p.time.timestamp()}")
        return keep

    return list(filter(keep_post, posts))


# This could just as well be part of fetch_new_user_posts
def post_posts(posts: list[Post], webhook: str | None):
    for post in reversed(posts):
        if send_post_to_webhook(post, webhook):
            update_last_sent(post.time)
        sleep(DISCORD_TIMEOUT)


def print_posts(posts: list[Post]):
    for post in reversed(posts):
        print(f"""
=== New post from {post.author_display_name} ===
=== [url: {post.url} | posted at: {post.time}]
vvv [embeds: {post.embeds}] vvv
{post.content}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
""")


def optional(key: str, val) -> dict[str, str]:
    return {key: str(val)} if val is not None else {}


def send_post_to_webhook(post: Post, webhook: str | None):
    if webhook is None:
        print(f"{post}")
        return False
    info(f"{post}")
    webhook_data = {
        "content": post.url,
        "username": "Bluesky",
        "avatar_url": "https://web-cdn.bsky.app/static/favicon.png",
        ### Custom embeds!
        # "embeds": [
        #     {
        #         "title": f"New Post from {post.author_display_name}",
        #         **optional("url", post.url),
        #         # "thumbnail": {
        #         #     **optional("url", post.author_avatar),
        #         # },
        #         "author": {
        #             "name": f"{post.author_display_name} (@{post.author_handle})",
        #             "url": "https://bsky.app/profile/" + post.author_handle,
        #             "icon_url": post.author_avatar,
        #         },
        #         "description": post.content,
        #         # "fields": [
        #         #     {
        #         #         "name": post.author_display_name,
        #         #         "value": f"[@{post.author_handle}]({post.author_profile_url})",
        #         #     },
        #         #     {
        #         #         "name": post.content,
        #         #         "value": "",
        #         #     }
        #         # ],
        #         "color": 1941746,
        #         "footer": {
        #             "text": "bsky.app",
        #         },
        #         "timestamp": post.time.isoformat(),
        #     },
        # ]
    }

    res = requests.post(url=webhook, json=webhook_data)
    if not res.ok:
        warning(f"Sending webhook failed: {res.content}")
    return res


def did_resolver(username):
    resolver = IdResolver()
    return resolver.handle.resolve(username)


def atUriToBskyAppUrl(at_uri: str, author_handle: str | None) -> (str | None):
    # at://did:plc:2vrama6qvld2tbwuokqvxzxq/app.bsky.feed.post/3lspbv6aq2c2o
    regex = re.compile('^at://([^/]+)/([^/]+)/([^/]+)$')
    match = regex.match(at_uri)

    print(f"[DEBUG] at_uri: {at_uri} | matches: {match}")

    if not match:
        return None  # Invalid AT URI format

    did = author_handle if author_handle is not None else match[1]
    collection = match[2]
    rkey = match[3]

    if collection == 'app.bsky.feed.post':
        return f"https://bsky.app/profile/{did}/post/{rkey}"
    else:
        return None  # Not a post record


def main():

    dryrun = False
    if "--dry-run" in sys.argv or "-n" in sys.argv:
        dryrun = True
        print("[INFO] Dry-run. No posts will be sent to the webhook")

    print("Logging in...")
    client = Client()
    client.login(USERNAME, PASSWORD)
    print("CONNECTED")

    if client.me is None:
        exit("Errör")
    else:
        mydid = client.me.did
        while True:
            if not dryrun: 
                post_posts(fetch_new_user_posts(client, mydid), WEBHOOK_URL)
            else:
                print_posts(fetch_new_user_posts(client, mydid))
            print(f"| | | WAITING for {TIMEOUT} minutes... ")
            sleep(60 * TIMEOUT)


if __name__ == "__main__":
    main()
