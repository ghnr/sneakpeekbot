from collections import defaultdict
from dataclasses import dataclass
import json
import re
import sys
import signal
from time import sleep, time
import traceback
import logging
import os
import praw
import prawcore.exceptions as pexcept
import praw.exceptions
from list_updater import update_lists
import constants as c
import utils


@dataclass
class SubmissionSummary:
    """A data summary of the top submissions found when gathering subreddit posts."""
    title: str
    url: str
    permalink: str
    num_comments: int
    is_nsfw: bool
    is_self: bool


@dataclass()
class RecentRecord:
    """A data holder for identifying spam patterns."""
    comment_author: str
    subreddit_name: str
    my_comment_id: str
    
    def __eq__(self, other):
        if isinstance(other, RecentRecord):
            return self.comment_author == other.comment_author and self.subreddit_name == other.subreddit_name
        return False


class SneakPeekBot:
    def __init__(self):
        self.counter = 0
        self.last_check_time = time()
        # Migrating to a database will do away with all this excess
        self.subreddit_blacklist = txt_to_list("lists/subreddit_blacklist.txt")
        self.subreddit_linking_blacklist = txt_to_list("lists/subreddit_linking_blacklist.txt")
        self.user_blacklist = txt_to_list("lists/user_blacklist.txt")
        self.posted_comments_id = txt_to_list("lists/comments_replied.txt")
        self.submissions = submissions_to_dict("lists/submissions.json")
        self.recent_spam_check = []

    @staticmethod
    def check_scores(first_run=False):
        """Check recently posted comments and delete if the karma score is below given threshold."""
        logger.info("Checking comment scores...")
        comment_limit = 500 if first_run else 100
        karma_threshold = 0 if first_run else 1

        for posted_comment in bot_profile.comments.new(limit=comment_limit):
            if posted_comment.score < karma_threshold:
                posted_comment.delete()
                url = posted_comment.permalink.replace(posted_comment.id, posted_comment.parent_id[3:])
                logger.info("Downvoted comment removed: https://www.reddit.com" + url)

    def check_inbox(self):
        """ Update blacklists by checking inbox for new blacklist requests."""
        update_lists()
        self.subreddit_blacklist = txt_to_list("lists/custom_blacklist.txt")
        self.user_blacklist = txt_to_list("lists/custom_blacklist_users.txt")

    def check_conditions(self, comment, subreddit_name, current_subreddit_name, found_subs):
        """ Check conditions that need to be met, returns True if comment can be processed."""
        conditions_met = False
        # Any match here will mean the comment is ignored
        ignore_conditions = [
            current_subreddit_name in self.subreddit_blacklist,
            subreddit_name in self.subreddit_linking_blacklist,
            comment.author in self.user_blacklist,
            current_subreddit_name == subreddit_name,
            comment.parent() in self.posted_comments_id,
            comment.is_root,
        ]

        if any(ignore_conditions):
            pass
        elif str(comment.submission) in self.submissions:
            if subreddit_name in self.submissions[str(comment.submission)]:
                logger.info("Subreddit already linked in this post: %s %s", str(comment.submission), subreddit_name)
            elif len(self.submissions[str(comment.submission)]) >= 3:
                logger.info("Already processed 3 comments in this thread: %s", str(comment.submission))
        elif re.findall("({}).*".format("|".join(c.REGEX_PATTERNS)), comment.body, flags=re.IGNORECASE):
            pass
        elif comment.author in comment.subreddit.moderator():
            # Extra API call is needed so this check is pushed as late as possible
            logger.info("Author is mod: %s in %s", comment.author, current_subreddit_name)
        else:
            conditions_met = True
        return conditions_met

    def process_comments_stream(self):
        """ Scan comments on /r/all for subreddit links to see if they meet conditions for processing
        and then process.
        The karma of recent comments is regularly assessed for deletion. The bot's inbox is also monitored for new
        blacklist requests.
        """
        logger.info("Scanning comments...")

        for comment in r_all.stream.comments():
            found_subs = re.search(r'<a href="/r/(\w+)">/?r/', comment.body_html)

            if not found_subs:
                continue

            subreddit_name = found_subs.group(1).lower()
            current_subreddit_name = str(comment.subreddit).lower()

            try:
                if self.check_conditions(comment, subreddit_name, current_subreddit_name, found_subs):
                    subreddit = reddit.subreddit(subreddit_name)
                    posts = self.get_top_subreddit_posts(subreddit)
                    message_string = self.build_string(posts, subreddit)
                    my_comment_id = self.send_reply(comment, message_string, subreddit)
                    self.save_ids(my_comment_id, str(comment.submission), subreddit.display_name)
                    self.check_recent_spam_list(comment.author.name, subreddit_name, my_comment_id)
                    self.counter += 1
                    logger.info(f"{self.counter} - {utils.format_elapsed_time(start_time)}")
            except praw.exceptions.RedditAPIException as e_api:
                logger.info("API Error: %s", str(e_api))
            except (pexcept.ServerError, pexcept.RequestException) as e_wait:
                logger.error("Server error: %s", str(e_wait))
                sleep(10)
            except (pexcept.Redirect, pexcept.NotFound) as e_404:
                logger.info("Subreddit doesn't exist: %s %s", subreddit_name, str(e_404))
            except pexcept.Forbidden as e_403:
                logger.warning("403 Error: %s %s", current_subreddit_name, str(e_403))
            except Exception:
                logger.exception("Exception:")
                traceback.print_exc()

            if self.counter == 10:
                try:
                    self.check_scores()
                    self.counter = 0
                except Exception:
                    logger.exception("Check_scores exception:")
                    traceback.print_exc()
                    sleep(15)
            if (time() - self.last_check_time) > c.INBOX_CHECK_FREQUENCY:
                self.check_inbox()
                self.last_check_time = time()
    
    @staticmethod
    def get_top_subreddit_posts(subreddit):
        """ Get the submission summary of the top 3 subreddit posts."""
        if (time() - subreddit.created_utc) / (60*60*24) > c.SUBREDDIT_AGE_THRESHOLD:
            # Subreddit is more than 3 years old
            time_filter = "year"
        else:
            time_filter = "all"

        summaries = []

        for submission in subreddit.top(time_filter=time_filter, limit=3):
            submission_summary = SubmissionSummary(
                submission.title,
                submission.url,
                submission.permalink,
                submission.num_comments,
                submission.over_18,
                submission.is_self
            )
            summaries.append(submission_summary)
            
        return summaries
    
    @staticmethod
    def build_string(submissions, subreddit):
       
        if len(submissions) < 3:
            logger.info("Less than 3 total posts: " + subreddit.display_name)
            return

        formatted_post_strings = []
        
        for summary in submissions:
            title = str(summary.title).replace("[", r"\[").replace("]", r"\]")
            nsfw_post_string = "**[NSFW]** " if summary.is_nsfw and not subreddit.over18 else ""
            post_url = summary.url.replace("//www.reddit.com/r/", "//np.reddit.com/r/") \
                .replace("(", "%28").replace(")", "%29")  # Breaks the markdown
            num_comments_plural = "" if summary.num_comments == 1 else "s"
            if summary.is_self:
                comments_link_string = ""
            else:
                comments_link_string = c.COMMENT_LINKS_PATTERN.format(
                    num_comments=summary.num_comments,
                    plural=num_comments_plural,
                    permalink=summary.permalink
                )
            
            post_string = c.INDIVIDUAL_POST_PATTERN.format(
                nsfw_post_string=nsfw_post_string,
                title=title,
                post_url=post_url,
                comments_link=comments_link_string
            )

            formatted_post_strings.append(post_string)

        nsfw_string = " **[NSFW]**" if subreddit.over18 else ""

        if (time() - subreddit.created_utc) / (60*60*24) > c.SUBREDDIT_AGE_THRESHOLD:
            # Subreddit is more than 3 years old
            time_filter_string = "the year"
            top_posts_link = f"https://np.reddit.com/r/{subreddit.display_name}/top/?sort=top&t=year"
        else:
            time_filter_string = "all time"
            top_posts_link = f"https://np.reddit.com/r/{subreddit.display_name}/top/?sort=top&t=all"

        message = c.HEADER + c.POSTS_PATTERN + c.FOOTER
        message = message.format(
            subreddit_name=subreddit.display_name,
            nsfw_string=nsfw_string,
            top_posts_link=top_posts_link,
            time_filter_string=time_filter_string,
            post_1=formatted_post_strings[0],
            post_2=formatted_post_strings[1],
            post_3=formatted_post_strings[2]
        )
        
        return message
    
    @staticmethod
    def send_reply(comment, message, subreddit):
        my_comment_id = str(comment.reply(message))
        logger.info("https://www.reddit.com" + comment.permalink)
        logger.info("Subreddit: %s %s", subreddit.display_name, subreddit.subscribers)
        return my_comment_id

    def check_recent_spam_list(self, comment_author, subreddit_name, my_comment_id):
        """ Checks recent comments processed for any pattern of spam. Deletes replies if spam."""
        new_record = RecentRecord(comment_author, subreddit_name, my_comment_id)
        self.recent_spam_check.append(new_record)
        # Only maintain N=25 of the most recent processed pairs
        if len(self.recent_spam_check) > c.NUM_RECENT_COMMENTS:
            del self.recent_spam_check[0]  # Appending to end so delete first element

        if self.recent_spam_check.count(new_record) >= 3:  # 3 strikes and you're out
            logger.info(f"Recent spam check found potential spammer {comment_author} posting {subreddit_name} - blacklisted")
            with open("lists/custom_blacklist_users.txt", "a") as users_blacklist_file:
                users_blacklist_file.write(comment_author + "\n")
            self.user_blacklist = txt_to_list("lists/user_blacklist.txt")

            # Delete all comments that match the spam
            records_to_delete = []
            for record in self.recent_spam_check:
                if record == new_record:
                    logger.info("Deleted recent comment matching spam pattern %s", record)
                    reddit.comment(record.my_comment_id).delete()
                    records_to_delete.append(record)
            # Clear up stale items in recents list
            for record in records_to_delete:
                self.recent_spam_check.remove(record)

    def save_ids(self, my_comment_id, submission_id, linked_subreddit):
        """ Saves to file the id of the comment reply by the bot and the id of the submission that the comment is in."""

        self.posted_comments_id.append(my_comment_id)

        with open("lists/comments_replied.txt", "w") as c_file:
            for posted_comment_id in self.posted_comments_id:
                c_file.write(posted_comment_id + "\n")

        self.submissions[submission_id].append(linked_subreddit.lower())

        with open("lists/submissions.txt", "w") as s_file:
            json.dump(self.submissions, s_file, sort_keys=True)


def txt_to_list(file_path):
    """ Returns a list from a .txt file."""
    return_list = []
    if os.path.isfile(file_path):
        with open(file_path, "r") as text_file:
            return_list = text_file.read()
            return_list = return_list.split("\n")
            return_list = list(filter(None, return_list))
            if file_path == "lists/comments_replied.txt":
                logger.info("Last comment id: %s", return_list[-1])
    return return_list


def submissions_to_dict(file_path):
    """ Returns a dict from a .json file."""
    submissions_dict = {}

    if os.path.isfile(file_path):
        with open(file_path, "r+") as submissions_file:
            # try/except is a band-aid fix to the issue of json file corrupting randomly
            submissions_dict = utils.repair_corrupt_json(submissions_file)
    return defaultdict(list, submissions_dict)


def config_logging():
    """ Log to console and to file."""
    config_logger = logging.getLogger("sneakpeekbot")
    config_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s: %(message)s - %(filename)s:%(funcName)s:%(lineno)d - %(asctime)s',
                                  datefmt='%H:%M:%S %Y/%m/%d')
    file_handler = logging.FileHandler('sneakpeek.log')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)
    config_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    config_logger.addHandler(console_handler)
    return config_logger


if __name__ == "__main__":
    logger = config_logging()
    logger.info("Starting up")

    signal.signal(signal.SIGTERM, utils.signal_handler)

    filter_list = txt_to_list("lists/filter_list.txt")

    reddit = praw.Reddit('sneakpeekbot', user_agent='sneakpeekbot 0.2')
    r_all = reddit.subreddit("all-" + "-".join(filter_list))
    bot_profile = reddit.redditor("sneakpeekbot")

    start_time = time()
    sneakpeekbot = SneakPeekBot()
    sneakpeekbot.check_scores(first_run=True)

    while True:
        sneakpeekbot.process_comments_stream()
