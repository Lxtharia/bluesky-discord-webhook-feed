# A small script to send posts from a bluesky account to a discord webhook

## Setup:
I've used [uv](https://github.com/astral-sh/uv) for package management, so you probably need that

Get yourself a discord webhook. You need to have that permission on the discord server though.
Go to the discord channel > Channel Settings > Integrations > Webhooks > New Webhook > Copy Webhook Url

## Usage:
Copy `example.env` to `.env` and set the needed fields
```
USERNAME=myuser.bsky.social
PASSWORD=XXXXXXXXX
WEBHOOK_URL=https://discord.com/api/webhooks/12345678890123456/.....
```
if you don't want to write your password in the file you can also just set it in your environment

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

Done. Leave a like and comment and don't forget to hit that notification bell!!1!



