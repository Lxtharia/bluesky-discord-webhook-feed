# A small script to send posts from a bluesky account to a discord webhook

## Setup (What you need):

I've used [**uv**](https://github.com/astral-sh/uv) for package management, so you probably need that

**A discord webhook.** To be able to create one, you need the permission on the discord server.

Go to the destination discord channel > Channel Settings > Integrations > Webhooks > New Webhook > Copy Webhook Url

**A bluesky account.** You need one.

**A password for your bluesky account.** Preferably an application password. Create one here: https://bsky.app/settings/app-passwords

## Usage:

Copy `example.env` to `.env` and set the required fields
```
### Your bluesky credentials
USERNAME=myuser.bsky.social
PASSWORD=XXXXXXXXX

WEBHOOK_URL=https://discord.com/api/webhooks/12345678890123456/.....
```
if you don't want to write your password in the file you can also just set it in your environment like this:

- On Linux:
  ```bash
  # Will prompt for your password, type blindly
  read -s PASSWORD
  export PASSWORD
  ```
- On Windows:
  ```powershell
  ... # TODO
  ```

Then just run
```bash
uv run main.py
```
and watch it first collect all past tweets before it sends it to the discord webhook.

Alternatively make it only fetch and print the posts instead of sending them to the webhook
```bash
uv run main.py -- --dry-run
```

Done. Leave a like and comment and don't forget to hit that notification bell!!1!



