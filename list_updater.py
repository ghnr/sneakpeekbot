import regex as re
import praw
from praw.models import SubredditMessage


def update_lists():
    """ Check inbox for new blacklist post replies, add new blacklist requests to blacklist."""
    banned_new = []
    users_new = []
    blacklist_new = []
    reddit = praw.Reddit('sneakpeekbot')
    
    for message in reddit.inbox.unread(limit=1000):
        # checks the blacklist thread for new replies
        if message.subject == "post reply" and message.parent_id[3:] == "8wfgsm":
            user_result = re.search("/?u/([a-zA-Z0-9_-]+)", message.body)
            subreddit_result = re.findall("/?r/(\w+)+", message.body)
            if user_result:
                # check if user commenting is the same as blacklist user request
                if user_result.group(1).lower() == str(message.author).lower():
                    users_new.append(str(message.author))
                    message.mark_read()
                    message.reply("Done")
            if subreddit_result:
                processed = False
                for sub in subreddit_result:
                    if sub.lower() not in blacklist_new:
                        subreddit_name = sub.lower()
                        subreddit_obj = reddit.subreddit(subreddit_name)
                        if message.author in subreddit_obj.moderator():
                            processed = True
                            blacklist_new.append(subreddit_obj.display_name.lower())
                if processed:
                    message.mark_read()
                    message.reply("Done")
        elif isinstance(message, SubredditMessage):
            ban_result = re.search("You've been banned from participating in /?r/(\w+)", message.subject)
            if ban_result and not message.author:
                subreddit = ban_result.group(1)
                message.mark_read()
                banned_new.append(subreddit.lower())
    
    with open("lists/banned.txt", "a") as f:
        for sub in banned_new:
            f.write(sub + "\n")
    
    with open("lists/custom_blacklist_users.txt", "a") as f:
        for user in users_new:
            f.write(user + "\n")
    
    with open("lists/custom_blacklist.txt", "a") as f:
        for b_sub in blacklist_new:
            f.write(b_sub + "\n")


if __name__ == '__main__':
    update_lists()
