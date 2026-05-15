# utils/transcript.py

import os
import io
import html
import discord

from datetime import datetime


# =========================
# CONFIG
# =========================

TRANSCRIPT_FOLDER = "data/transcripts"

os.makedirs(
    TRANSCRIPT_FOLDER,
    exist_ok=True
)


# =========================
# HTML ESCAPE
# =========================

def safe(text):

    if not text:
        return ""

    return html.escape(str(text))


# =========================
# FORMAT TIME
# =========================

def format_time(dt):

    return dt.strftime(
        "%d/%m/%Y %H:%M"
    )


# =========================
# PARSE EMBEDS
# =========================

def parse_embeds(message):

    if not message.embeds:
        return ""

    result = ""

    for embed in message.embeds:

        title = safe(embed.title)
        description = safe(embed.description)

        fields_html = ""

        for field in embed.fields:

            fields_html += f"""
            <div class="embed-field">
                <div class="embed-field-name">
                    {safe(field.name)}
                </div>

                <div class="embed-field-value">
                    {safe(field.value)}
                </div>
            </div>
            """

        result += f"""
        <div class="embed-box">

            <div class="embed-title">
                {title}
            </div>

            <div class="embed-description">
                {description}
            </div>

            {fields_html}

        </div>
        """

    return result


# =========================
# PARSE ATTACHMENTS
# =========================

def parse_attachments(message):

    if not message.attachments:
        return ""

    html_data = ""

    for attachment in message.attachments:

        filename = safe(
            attachment.filename
        )

        url = attachment.url

        # IMAGE
        if attachment.content_type:

            if attachment.content_type.startswith(
                "image"
            ):

                html_data += f"""
                <div class="attachment">

                    <img
                        src="{url}"
                        class="attachment-image"
                    >

                </div>
                """

                continue

        # FILE
        html_data += f"""
        <div class="attachment">

            📎
            <a href="{url}">
                {filename}
            </a>

        </div>
        """

    return html_data


# =========================
# BUILD MESSAGE
# =========================

async def build_message(message):

    avatar = message.author.display_avatar.url

    username = safe(
        str(message.author)
    )

    timestamp = format_time(
        message.created_at
    )

    content = safe(
        message.content
    ).replace(
        "\n",
        "<br>"
    )

    embeds = parse_embeds(
        message
    )

    attachments = parse_attachments(
        message
    )

    return f"""
    <div class="message">

        <img
            class="avatar"
            src="{avatar}"
        >

        <div class="message-body">

            <div class="message-header">

                <span class="username">
                    {username}
                </span>

                <span class="timestamp">
                    {timestamp}
                </span>

            </div>

            <div class="content">
                {content}
            </div>

            {embeds}

            {attachments}

        </div>

    </div>
    """


# =========================
# GENERATE HTML TRANSCRIPT
# =========================

async def generate_transcript(
    channel: discord.TextChannel
):

    messages_html = []

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):

        try:

            html_message = await build_message(
                message
            )

            messages_html.append(
                html_message
            )

        except Exception as error:

            print(
                f"[TRANSCRIPT ERROR] {error}"
            )

    final_html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<title>
Transcript - {channel.name}
</title>

<style>

body {{
    background-color: #1e1f22;
    color: white;
    font-family: Arial;
    padding: 20px;
}}

.header {{
    text-align: center;
    margin-bottom: 40px;
}}

.message {{
    display: flex;
    margin-bottom: 25px;
}}

.avatar {{
    width: 45px;
    height: 45px;
    border-radius: 50%;
    margin-right: 15px;
}}

.message-body {{
    background-color: #2b2d31;
    padding: 12px;
    border-radius: 10px;
    width: 100%;
}}

.message-header {{
    margin-bottom: 8px;
}}

.username {{
    color: #5865f2;
    font-weight: bold;
}}

.timestamp {{
    color: #9a9a9a;
    margin-left: 10px;
    font-size: 12px;
}}

.content {{
    white-space: pre-wrap;
}}

.embed-box {{
    margin-top: 10px;
    padding: 10px;
    border-left: 4px solid #5865f2;
    background-color: #1e1f22;
    border-radius: 6px;
}}

.embed-title {{
    font-weight: bold;
    margin-bottom: 5px;
}}

.embed-description {{
    margin-bottom: 5px;
}}

.embed-field {{
    margin-top: 8px;
}}

.embed-field-name {{
    font-weight: bold;
}}

.attachment {{
    margin-top: 10px;
}}

.attachment-image {{
    max-width: 500px;
    border-radius: 8px;
}}

a {{
    color: #00a8fc;
    text-decoration: none;
}}

</style>

</head>

<body>

<div class="header">

<h1>
🎫 Ticket Transcript
</h1>

<p>
Channel:
#{channel.name}
</p>

<p>
Guild:
{safe(channel.guild.name)}
</p>

<p>
Generated:
{format_time(datetime.utcnow())}
</p>

</div>

{''.join(messages_html)}

</body>

</html>
"""

    file_path = (
        f"{TRANSCRIPT_FOLDER}/"
        f"{channel.id}.html"
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(final_html)

    return file_path


# =========================
# HTML FILE OBJECT
# =========================

async def transcript_file(
    channel: discord.TextChannel
):

    path = await generate_transcript(
        channel
    )

    return discord.File(
        path,
        filename=f"{channel.name}.html"
    )


# =========================
# TEXT TRANSCRIPT
# =========================

async def text_transcript(
    channel: discord.TextChannel
):

    logs = []

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):

        timestamp = format_time(
            message.created_at
        )

        content = (
            message.content
            if message.content
            else "[Embed/Attachment]"
        )

        logs.append(
            f"[{timestamp}] "
            f"{message.author}: "
            f"{content}"
        )

    data = "\n".join(logs)

    file = io.BytesIO(
        data.encode()
    )

    return discord.File(
        file,
        filename=f"{channel.name}.txt"
    )
