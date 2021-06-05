import tokens, os
from quart import Quart, redirect, url_for, render_template, request
from urllib import parse
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from quart_motor import Motor
app = Quart(__name__)

async def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

app.config["DISCORD_CLIENT_ID"] = 850193630760009748
app.config["DISCORD_CLIENT_SECRET"] = tokens.client_secret
app.config["DISCORD_REDIRECT_URI"] = "https://grain.party/callback"
app.secret_key = tokens.secret_key
app.config["MONGO_URI"] = tokens.mongo
mongo = Motor(app)
discord = DiscordOAuth2Session(app)
app.after_request(add_header)

@app.route('/index')
@app.route('/index.html')
@app.route('/')
async def index():
    current_msg = ''
    messages = await mongo.db.messages.find({}).to_list(None)
    try:
        user = await discord.fetch_user()
        for x in messages:
            if x['id'] == user.id:
                current_msg = x['message']
        username = user.name
    except Unauthorized:
        user = False
        username = None
    return await render_template('index.html', text_entry=current_msg, number=len(messages), username=username, user=user)

@app.route("/login")
async def login():
    return await discord.create_session(scope=['identify'])

@app.route("/callback")
async def callback():
    await discord.callback()
    return redirect(url_for("index"))

@app.route("/admin")
@requires_authorization
async def admin():
    user = await discord.fetch_user()
    if user.id not in [519482266473332736, 443217277580738571, 811051750802325545]:
        return redirect(url_for("index"))
    messages = await mongo.db.messages.find({}).to_list(None)
    return await render_template('admin.html', messages=messages, message_count=len(messages))

@app.route('/update', methods=["POST"])
@requires_authorization
async def update():
    data = await request.form
    user = await discord.fetch_user()
    await mongo.db.messages.find_one_and_update({"id": user.id}, {"$set": {"name": user.name, "avatar": user.avatar_url, "message": data["message"]}}, upsert=True)
    return redirect(f"{url_for('index')}?updated")

@app.route('/logout')
@requires_authorization
async def logout():
    discord.revoke()
    return redirect(url_for('index'))

@app.errorhandler(InvalidGrantError)
@app.errorhandler(Unauthorized)
def handle_unauthorized(e):
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=False)
