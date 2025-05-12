from datetime import datetime
from atproto import Client, IdResolver
from time import sleep

import os
from atproto_client.models.app.bsky.feed.defs import FeedViewPost, PostView
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

TIMEOUT = 2
LAST_SENT_TIMESTAMP = 0


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


def process_user_posts(client: Client, webhook: str | None, user_did: str, last_sent) -> list[Post]:
    next_handle = user_did
    while next_handle is not None:
        data = client.get_author_feed(
            actor=next_handle,
            filter='posts_and_author_threads',
            limit=30,
        )
        # For paging
        next_handle = data.cursor
        feed = data.feed
        for feedpost in feed:
            post = Post(feedpost)
            # Skip already seen posts
            if post.time.timestamp() <= datetime.fromtimestamp(last_sent).timestamp():
                continue

            post_post(webhook, post)
            sleep(TIMEOUT)
    return []


def did_resolver(username):
    resolver = IdResolver()
    return resolver.handle.resolve(username)


def post_post(webhook: str | None, post: Post):
    if webhook is None:
        print(f"Post: {post}")
        return


def main():
    print("Logging in...")
    client = Client()
    client.login(USERNAME, PASSWORD)
    print("CONNECTED")

    if client.me is None:
        exit("Errör")
    else:
        mydid = client.me.did
        process_user_posts(client, WEBHOOK_URL, mydid, LAST_SENT_TIMESTAMP)


if __name__ == "__main__":
    main()
