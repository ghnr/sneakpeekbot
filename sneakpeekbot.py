import os
import json
import time
import signal
import logging
import traceback
import regex as re
from itertools import chain
import praw
import prawcore.exceptions as pexcept
import list_updater
import constants as c


class SneakPeekBot:
    def __init__(self):
        self.counter = 0
        self.last_check_time = time.time()
    
    def check_scores(self, first_run=False):
        """Check recently posted comments, delete if karma score below threshold."""
        logger.info("Checking comment scores...")
        comment_limit = 500 if first_run else 100
        threshold = 0 if first_run else 1
        
        for posted_comment in bot_profile.comments.new(limit=comment_limit):
            if posted_comment.score < threshold:
                url = posted_comment.permalink.replace(posted_comment.id, posted_comment.parent_id[3:])
                logger.info("Downvoted comment removed: https://www.reddit.com" + url)
                posted_comment.delete()
        self.counter = 0
    
    @staticmethod
    def check_inbox():
        """ Update blacklists by checking inbox for new blacklist requests."""
        list_updater.update_lists()
        custom_blacklist[:] = txt_to_list('custom_blacklist.txt')
        custom_blacklist_users[:] = txt_to_list('custom_blacklist_users.txt')
        banned[:] = txt_to_list('banned.txt')
    
    def scan_comments(self):
        """ Scan comments on /r/all for subreddit links
        check if they meet conditions for processing and then process."""
        
        logger.info("Scanning comments...")
        
        for comment in r_all.stream.comments():
            if self.counter == 10:
                self.check_scores()
            elif (time.time() - self.last_check_time) > 3 * 60 * 60:
                # elif used so that the bot doesn't fall too far behind the stream
                self.check_inbox()
                self.last_check_time = time.time()
            
            subreddits_found = re.findall(r'<a href="/r/(\w+)">/?r/', comment.body_html)
            if not subreddits_found:
                continue
            
            # value is either True or None
            summoned = re.search("\+/?u/sneakpeekbot", comment.body)
            
            # multiple subreddits to be checked soon
            subreddit_name = subreddits_found[0].lower()
            
            if self.check_conditions(comment, subreddit_name, subreddits_found, summoned):
                try:
                    self.process_comment(subreddit_name, comment, summoned=summoned)
                except (praw.exceptions.APIException, pexcept.Redirect, pexcept.NotFound,
                        pexcept.Forbidden) as e_known:
                    logger.info("Known error: " + str(e_known))
                except (pexcept.ServerError, pexcept.RequestException) as e_wait:
                    logger.error("Request/Server error: " + str(e_wait))
                    time.sleep(5)
                except Exception:
                    # log uncaught exceptions for fixing
                    logger.exception("Error:")
                    traceback.print_exc()
    
    def check_conditions(self, comment, subreddit_name, found_subs, summoned):
        """ Check conditions that need to be met before processing the comment."""
        conditions_met = False
        
        if summoned:
            # being explicitly summoned is subject to fewer checks
            logger.warning("Summoned by {} in {}".format(comment.author, comment.subreddit))
            summon_conditions = [comment.subreddit not in banned,
                                 comment.subreddit not in custom_blacklist,
                                 subreddit_name not in custom_ignore_link,
                                 comment.author not in bot_users]
            if all(summon_conditions):
                return True
        
        # "not" used to make it clear what we are checking for
        conditions = [subreddit_name not in chain(top500subs, memes, bot_subreddits, custom_ignore_link),
                      comment.author not in chain(bot_users, custom_blacklist_users),
                      comment.subreddit != subreddit_name,
                      comment.subreddit not in chain(banned, custom_blacklist),
                      comment.parent() not in posted_comments_id,
                      not comment.is_root,
                      len(set(found_subs)) <= 2]
        
        submission_id = comment.submission.id
        
        if not all(conditions):
            if submission_id in submissions:
                if subreddit_name in submissions[submission_id]:
                    logger.info(
                        "Subreddit already linked in this post: {} {}".format(submission_id, subreddit_name))
                elif len(submissions[submission_id]) >= 3:
                    logger.info("Already processed 3 comments in this thread: " + comment.submission.id)
            elif re.findall("({}).*".format('|'.join(c.REGEX_PATTERNS)), comment.body, flags=re.IGNORECASE):
                with open('comments_flagged.txt', 'a', encoding='utf-8') as flagged_file:
                    flagged_file.write(comment.body + "\n\n")
            elif comment.author in comment.subreddit.moderator():
                logger.info("Author is mod: {} in {}".format(comment.author, comment.subreddit))
            else:
                conditions_met = True
        return conditions_met
    
    def process_comment(self, subreddit_name, comment, summoned=False):
        """ Start building the reply string from the top 3 subreddit posts.
        After the reply string is finished, post the reply and save the IDs."""
        
        subreddits = [subreddit_name]
        in_nsfw_subreddit = comment.subreddit.over18
        subreddits_processed = 0
        num_subreddit_limit = 3
        
        comment_string_body = ""
        if summoned:
            subreddits_found = re.findall("/?r/(\w+)+", comment.body)
            for unique_subreddit in subreddits_found:
                if unique_subreddit not in subreddits:
                    subreddits.append(unique_subreddit)
            if len(subreddits) > 1:
                comment_string_header = c.HEADER_SUMMONED
            else:
                comment_string_header = c.HEADER_SUMMONED_SINGLE
            posts_string_pattern = c.POSTS_PATTERN_SUMMONED
        else:
            comment_string_header = c.HEADER
            posts_string_pattern = c.POSTS_PATTERN
        
        for subreddit_names in subreddits:
            subreddit = reddit.subreddit(subreddit_names)
            
            # check if subreddit more than 3 years old
            sub_age_threshold = 3 * 365
            if (time.time() - subreddit.created_utc) / (60 * 60 * 24) > sub_age_threshold and not summoned:
                time_filter = "year"
                time_filter_string = "the year"
                top_posts_link = 'https://np.reddit.com/r/{}/top/?sort=top&t=year'.format(subreddit.display_name)
            else:
                time_filter = "all"
                time_filter_string = "all time"
                top_posts_link = 'https://np.reddit.com/r/{}/top/?sort=top&t=all'.format(subreddit.display_name)
                
            # the subreddit definition is lazy loaded so exceptions are checked at first call instead
            try:
                success, subreddit_string, posts = self.process_subreddit(subreddit, in_nsfw_subreddit, time_filter,
                                                                          summoned=summoned)
                if not success:
                    continue
            except (pexcept.Redirect, pexcept.NotFound, pexcept.Forbidden):
                continue
                       
            if summoned:
                post_strings = posts_string_pattern.format(subreddit_string, posts[0], posts[1], posts[2])
            else:
                # assumed only 1 subreddit so can end
                comment_string_header = comment_string_header.format(subreddit_string, top_posts_link,
                                                                     time_filter_string)
                post_strings = posts_string_pattern.format(posts[0], posts[1], posts[2])
            
            comment_string_body += post_strings
            subreddits_processed += 1
            
            if subreddits_processed == num_subreddit_limit:
                break
        
        if subreddits_processed != len(subreddits):
            if subreddits_processed >= 1:
                plural = "s" if subreddits_processed > 1 else ""
                comment_string_body += "(Only showing {} subreddit{} out of the {} linked)  \n\n".format(
                    subreddits_processed, plural, len(subreddits))
            else:
                return
        
        message = comment_string_header + comment_string_body + c.FOOTER
        my_comment_id = str(comment.reply(message))
        self.save_ids(comment.id, my_comment_id, comment.submission.id, subreddits)
        logger.info("https://www.reddit.com" + comment.permalink)

    def process_subreddit(self, linked_subreddit, in_nsfw_subreddit, time_filter, summoned=False):
        """ Retrieve subreddit properties to bundle with top posts."""
        success = True
    
        nsfw_sub_link = linked_subreddit.over18
        if summoned and nsfw_sub_link and not in_nsfw_subreddit:
            success = False
    
        subreddit_np = "/r/" + linked_subreddit.display_name
        nsfw_string = " **[NSFW]**" if linked_subreddit.over18 else ""
        subreddit_string = subreddit_np + nsfw_string
    
        top_posts = list(self.parse_top_posts(linked_subreddit, time_filter=time_filter))
    
        if len(top_posts) < 3:
            success = False
    
        return success, subreddit_string, top_posts
    
    @staticmethod
    def parse_top_posts(subreddit, time_filter):
        """ Retrieves the top 3 posts of a subreddit and sanitises the output."""
        for submission in subreddit.top(time_filter=time_filter, limit=3):
            nsfw_post_string = "**[NSFW]** " if submission.over_18 and not subreddit.over18 else ""
            # certain characters will break the markdown formatting, escape them
            title = submission.title.replace('[', '\[').replace(']', '\]')
            if title.endswith('\\'):
                title = title[:-1] + '\ '
            post_url = submission.url.replace('//www.reddit.com', '//np.reddit.com').replace('(', '%28').replace(')',
                                                                                                                 '%29')
            comments_link_string = ""
            if not submission.is_self:
                if submission.num_comments > 1 or submission.num_comments == 0:
                    plural = "s"
                else:
                    plural = ""
                comments_link_string = " | [{} comment{}](https://np.reddit.com{})".format(submission.num_comments,
                                                                                           plural, submission.permalink)
            comment_format = "[{}{}]({}){}".format(nsfw_post_string, title, post_url, comments_link_string)
            yield comment_format
    
    def save_ids(self, comment_ID, my_comment_ID, submission_ID, linked_subreddits):
        """ Save comment and submission IDs to local file."""
        # ID of comment replied to
        posted_comments_id.append(comment_ID)
        # ID of comment posted
        posted_comments_id.append(my_comment_ID)
        
        with open('lists/comments_replied.txt', 'w') as c_file:
            for comment_ID in posted_comments_id:
                c_file.write(comment_ID + "\n")
        
        for subreddit in linked_subreddits:
            if submission_ID in submissions:
                submissions[submission_ID].append(subreddit.lower())
            else:
                submissions[submission_ID] = [subreddit.lower()]
        
        with open('lists/submissions.txt', 'w') as s_file:
            json.dump(submissions, s_file, sort_keys=True)
        
        self.counter += 1


# noinspection PyUnusedLocal
def signal_handler(var1, var2):
    """ Signal handler for cloud server management"""
    logger.info("Handled signal")


def txt_to_list(file_path):
    """ Returns a list from a .txt file"""
    return_list = []
    file_path = os.path.join('lists', file_path)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as txt_file:
            return_list = txt_file.read()
            return_list = return_list.split("\n")
            return_list = list(filter(None, return_list))
    return return_list


def config_logging():
    """ log to console and to file."""
    logger = logging.getLogger('sneakpeekbot')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s: %(message)s - %(filename)s:%(funcName)s:%(lineno)d - %(asctime)s',
                                  datefmt='%H:%M:%S %Y/%m/%d')
    file_handler = logging.FileHandler('sneakpeek.log')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


if __name__ == '__main__':
    logger = config_logging()
    logger.info("Starting up")
    
    signal.signal(signal.SIGTERM, signal_handler)
    
    # moving to a database will do away with all this excess
    posted_comments_id = txt_to_list('comments_replied.txt')
    filter_list = txt_to_list('filter_list.txt')
    custom_blacklist = txt_to_list('custom_blacklist.txt')
    custom_blacklist_users = txt_to_list('custom_blacklist_users.txt')
    custom_ignore_link = txt_to_list('custom_ignore_link.txt')
    banned = txt_to_list('banned.txt')
    bot_users = txt_to_list('bot_users.txt')
    bot_subreddits = txt_to_list('bot_subreddits.txt')
    memes = txt_to_list('memes.txt')
    top500subs = txt_to_list('top500subs.txt')
    submissions = {}
    
    if os.path.isfile('lists/submissions.txt'):
        with open('lists/submissions.txt', 'r+') as f:
            # try/except is a band-aid fix to the issue of json file corrupting randomly
            try:
                submissions = json.load(f)
            except json.decoder.JSONDecodeError:
                # seek to end of file for writing and back to start for reading
                logger.error("JSON file corrupted: ")
                f.seek(0, os.SEEK_END)
                f.write("]}")
                f.seek(0)
                submissions = json.load(f)
    
    reddit = praw.Reddit('sneakpeekbot')
    r_all = reddit.subreddit('all-' + '-'.join(filter_list))
    bot_profile = reddit.redditor('sneakpeekbot')
    
    sneakpeekbot = SneakPeekBot()
    sneakpeekbot.check_scores(first_run=True)
    
    while True:
        try:
            sneakpeekbot.scan_comments()
        except (pexcept.ServerError, pexcept.Forbidden, pexcept.RequestException, pexcept.ResponseException) as e_known:
            logger.error("Main while loop error (known): " + e_known)
        except Exception:
            # Logging uncaught exceptions to fix later
            logger.exception("Main while loop error:")
            traceback.print_exc()
            time.sleep(15)
