# clawd digest

privacy-conscious twitter feed summarizer → daily email digest

(named clawd because we were gonna use clawdbot and then i didn't but the name stuck)

## setup

### 1. get twitter api credentials
- go to https://developer.twitter.com/
- create app, generate: api key, api secret, bearer token, access token, access token secret
- **free tier = 100 posts/month.** daily runs = 30/month, so default is 3 tweets/run (3 × 30 = 90). optional: set `TWITTER_MAX_RESULTS` higher if you run less often (e.g. weekly = 25/run). cap resets monthly (see your project dashboard).

### 2. get anthropic api key
- go to https://console.anthropic.com/
- create api key

### 3. gmail app password
- use a gmail account for sending
- turn on 2fa, then create an app password: https://myaccount.google.com/apppasswords
- set `EMAIL_FROM` to that gmail address, `EMAIL_APP_PASSWORD` to the app password, `EMAIL_TO` to where you want the digest (can be same or different)

### 4. add github actions secrets
in your repo: settings → secrets and variables → actions. add:
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_BEARER_TOKEN`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`
- `ANTHROPIC_API_KEY`
- `EMAIL_FROM`
- `EMAIL_APP_PASSWORD`
- `EMAIL_TO`
- (optional) `TWITTER_MAX_RESULTS` – tweets per run, default 3 (for daily runs under 100/month).

### 5. push
workflow runs daily at 3pm pacific (23:00 UTC). you can also run it manually: actions → daily twitter digest → run workflow.

## architecture

see [`architecture.mmd`](architecture.mmd) for system flow diagram

**how it works:**
1. github actions runs on schedule (3pm pacific)
2. script fetches your twitter home timeline (last 24 hours, sorted by engagement)
3. script calls anthropic api to summarize
4. script sends summary by email (gmail smtp)
5. no persistent storage; raw tweets discarded after run

**yes, this works with your specific twitter feed.** the script uses twitter api's home timeline endpoint – same tweets you see when you open twitter.

## privacy
- no persistent storage; raw tweets discarded after each run
- only the summary is sent to your email
- credentials live in github secrets only (or in local `.env` when testing)
