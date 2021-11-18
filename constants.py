
# Markdown syntax for the bot's message
HEADER = "Here's a sneak peek of /r/{subreddit_name}{nsfw_string} using the [top posts]({top_posts_link}) of {time_filter_string}!\n\n"
POSTS_PATTERN = "\#1: {post_1}  \n\#2: {post_2}  \n\#3: {post_3}\n\n----\n"
INDIVIDUAL_POST_PATTERN = "[{nsfw_post_string}{title}]({post_url}){comments_link}"
COMMENT_LINKS_PATTERN = " | [{num_comments} comment{plural}](https://np.reddit.com{permalink})"
FOOTER = "^^I'm ^^a ^^bot, ^^beep ^^boop ^^| ^^Downvote ^^to ^^remove ^^| ^^[Contact](https://www.reddit.com/message/compose/?to=sneakpeekbot)" \
" ^^| ^^[Info](https://np.reddit.com/r/sneakpeekbot/) ^^| ^^[Opt-out](https://np.reddit.com/r/sneakpeekbot/comments/o8wk1r/blacklist_ix/)" \
" ^^| ^^[Source](https://github.com/ghnr/sneakpeekbot)"

# Magic numbers
INBOX_CHECK_FREQUENCY = 3 * 60 * 60  # 3 hours
SUBREDDIT_AGE_THRESHOLD = 1095  # 3 years in days
NUM_RECENT_COMMENTS = 25

REGEX_PATTERNS = [
    r"/?r/\w+ has a [a-z]{3,}?ly",
    r"((?<!top posts)\sover (?:to|in|at) /?r/)",
    r"((?<!top post)\sover (?:to|in|at) /?r/)",
    r"also,? check out /r/",
    r"you can check /r/",
    r"ask (?:this\s)?(?:in\s|at\s)?/?r/",
    r"ask the [a-z]+ (?:on|in) /?r/",
    r"OP in /?r/"
    r"go to /?r/\w+ and search",
    r"asking in /?r/",
    r"I asked in /?r/",
    r"try asking (?:this\s)?on /?r/",
    r"try /r/\w+\?",
    r"(?:can|could) you post (?:this\s)?to /?r/",
    r"/?r/\w+'s sidebar",
    r"asking (?:this\s)?over at /?r/",
    r"your question (?:in|on|to) /?r/",
    r"post this (?:in|on|to) /?r/",
    r"post it (?:in|on|to) /?r/",
    r"posted (?:in|on|to) /?r/",
    r"posting (?:in|on|to) /?r/",
    r"repost (?:in|on|to) /?r/",
    r"(?:she|he) posted on /?r/",
    r"try posting (?:this\s)?in /?r/",
    r"have you tried /?r/",
    r"mod(?:erator)?s? (?:of|in|on|for) /?r/",
    r"/?r/\w+ is (?:a\s)shit",
    r"I'm not subbed to /?r/",
    r"I am not subbed to /?r/",
    r"unsubscribe from /?r/",
    r"I hate /?r/",
    r"(?:run|go) back to /?r/",
    r"(?:deleted|banned) from /?r/",
    r"selling in /?r/",
    r"~~/r/\w+~~",
    r"(?:^\s*>|\s*>)[^\\\n]+/r/\w+[^\\\n\\\n]+"
]
