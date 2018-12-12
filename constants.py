HEADER_SUMMONED = "Hi, here's a sneak peek of those subreddits using the top posts of all time!\n\n"
HEADER_SUMMONED_SINGLE = "Hi, here's a sneak peek of that subreddit using the top posts of all time!\n\n"
HEADER = "Here's a sneak peek of {} using the [top posts]({}) of {}!\n\n"
POSTS_PATTERN_SUMMONED = "**{}**:\n\n\#1: {}  \n\#2: {}  \n\#3: {}\n\n"
POSTS_PATTERN = "\#1: {}  \n\#2: {}  \n\#3: {}\n\n"
FOOTER = "----\n^^I'm ^^a ^^bot, ^^beep ^^boop ^^| ^^Downvote ^^to ^^remove ^^| [^^Contact ^^me](https://www.reddit.com/message/compose/?to=sneakpeekbot) ^^| [^^Info](https://np.reddit.com/r/sneakpeekbot/) ^^| [^^Opt-out](https://np.reddit.com/r/sneakpeekbot/comments/8wfgsm/blacklist/)"
REGEX_PATTERNS = ["/?r/\w+ has a [a-z]{3,}?ly",
                  "((?<!top posts)\sover (?:to|in|at) /?r/)",
                  "((?<!top post)\sover (?:to|in|at) /?r/)",
                  "also,? check out /r/",
                  "you can check /r/",
                  "ask (?:this\s)?(?:in\s|at\s)?/?r/",
                  "ask the [a-z]+ (?:on|in) /?r/",
                  "OP in /?r/"
                  "go to /?r/\w+ and search",
                  "asking in /?r/",
                  "I asked in /?r/",
                  "try asking (?:this\s)?on /?r/",
                  "try /r/\w+\?",
                  "(?:can|could) you post (?:this\s)?to /?r/",
                  "/?r/\w+'s sidebar",
                  "asking (?:this\s)?over at /?r/",
                  "your question (?:in|on|to) /?r/",
                  "post this (?:in|on|to) /?r/",
                  "post it (?:in|on|to) /?r/",
                  "posted (?:in|on|to) /?r/",
                  "posting (?:in|on|to) /?r/",
                  "repost (?:in|on|to) /?r/",
                  "(?:she|he) posted on /?r/",
                  "try posting (?:this\s)?in /?r/",
                  "have you tried /?r/",
                  "mod(?:erator)?s? (?:of|in|on|for) /?r/",
                  "/?r/\w+ is (?:a\s)shit",
                  "I'm not subbed to /?r/",
                  "I am not subbed to /?r/",
                  "unsubscribe from /?r/",
                  "I hate /?r/",
                  "(?:run|go) back to /?r/",
                  "(?:deleted|banned) from /?r/",
                  "selling in /?r/",
                  "~~/r/\w+~~",
                  "(?:^\s*>|\s*>)[^\\\n]+/r/\w+[^\\\n\\\n]+"]
