from datetime import datetime
from atproto import Client, IdResolver
from time import sleep

import os
from atproto_client.models.app.bsky.feed.defs import FeedViewPost, PostView
from atproto_client.models.app.bsky.feed.get_feed import Params
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

LAST_SENT_AT_FILENAME = "last_sent_at.txt"

USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

TIMEOUT = 2


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
    with open(LAST_SENT_AT_FILENAME, 'w') as f:
        f.write(f"last_sent_at={time.timestamp()}")


def read_last_sent():
    timestamp = 0
    if os.path.exists(LAST_SENT_AT_FILENAME):
        with open(LAST_SENT_AT_FILENAME, 'r') as f:
            timestamp = f.read().split(sep='=')[1]
    return datetime.fromtimestamp(float(timestamp))


def process_user_posts(client: Client, webhook: str | None, user_did: str):
    next_page = None
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
        last_sent_at = read_last_sent()

        reached_end = False
        for feedpost in reversed(feed):
            post = Post(feedpost)

            # Skip already seen posts
            if post.time.timestamp() <= last_sent_at.timestamp():
                reached_end = True  # No need to paginate further
                print(f"<Skipping post from @{post.time.timestamp()}>")
                continue

            if post_post(webhook, post):
                update_last_sent(post.time)

            sleep(TIMEOUT)

        print(next_page)
        if reached_end or next_page is None:
            break


def did_resolver(username):
    resolver = IdResolver()
    return resolver.handle.resolve(username)


def post_post(webhook: str | None, post: Post):
    if webhook is None:
        print(f"Post: {post}")
        return True


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
            process_user_posts(client, WEBHOOK_URL, mydid)
            sleep(60*5)


if __name__ == "__main__":
    main()
