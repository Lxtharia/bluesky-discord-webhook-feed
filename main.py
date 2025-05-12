from datetime import datetime
import logging
import sys
from atproto import Client, IdResolver
from time import sleep

import os
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
        self.author = post.post.author.handle
        self.author_display_name = post.post.author.display_name
        self.author_avatar = post.post.author.avatar
        self.content = post.post.record.text
        self.embeds = post.post.record.embed
        self.time: datetime = datetime.fromisoformat(post.post.indexed_at)

    def __format__(self, format_spec: str, /) -> str:
        return f"""<Post by '@{self.author}' at [{self.time.isoformat()}]:
                '{self.content}' with {"No" if self.embeds is None else ""} embeds>"""


def update_last_sent(time: datetime):
    info(f"Updating to {time.timestamp()}")
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
        if not keep: print(f"<Skipping post from {p.time.isoformat()} @{p.time.timestamp()}>")
        return keep

    return list(filter(keep_post, posts))


# This could just as well be part of fetch_new_user_posts
def post_posts(posts: list[Post], webhook: str | None):
    for post in reversed(posts):
        if send_post_to_webhook(post, webhook):
            update_last_sent(post.time)
        sleep(DISCORD_TIMEOUT)


def send_post_to_webhook(post: Post, webhook: str | None):
    if webhook is None:
        print(f"Post: {post}")
    return True


def did_resolver(username):
    resolver = IdResolver()
    return resolver.handle.resolve(username)


def main():
    print("Logging in...")
    client = Client()
    client.login(USERNAME, PASSWORD)
    print("CONNECTED")

    if client.me is None:
        exit("Errör")
    else:
        mydid = client.me.did
        while True:
            post_posts(fetch_new_user_posts(client, mydid), WEBHOOK_URL)
            print(" . . . WAITING . . . ")
            sleep(60 * TIMEOUT)


if __name__ == "__main__":
    main()
