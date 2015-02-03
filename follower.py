__author__ = 'mcs'
import requests
from bs4 import BeautifulSoup
import getopt
import sys
import re
import urlparse


class WikipediaFollower():

    def __init__(self, start=None):
        self.schema = "http://"
        self.wiki_prefix = self.schema + "en.wikipedia.org/"
        if start is None:
            self.start_link = self.wiki_prefix + "wiki/Special:Random"
        else:
            self.start_link = start
        self.stop_links = [self.wiki_prefix + "wiki/Philosophy"]
        self.visited_links = {}

    def crawl(self):
        """
        Begin crawling at the specified start link
        :return:
        """
        self.crawl_recur(self.start_link)

    def crawl_over(self, url):
        """
        return true if the crawl is over, false otherwise
        :param url: the current url
        :return: true if the crawl is over, false otherwise
        """
        return url in self.stop_links

    @staticmethod
    def has_special_wiki_keyword(next_link):
        """
        Wikipedia urls sometimes have special keywords in their links.
        Checks url format for similarity to http://en.wikipedia.org/wiki/File:...
        or http://en.wikipedia.org/wiki/Help:...
        :param next_link:
        :return: true if meets that format requirement.
        """
        return re.search("/wiki/.+?:", next_link) is not None

    def should_visit_link(self, next_link):
        """
        check if link valid to be visited
        :param next_link:
        :return: true if link valid to be visited, false otherwise
        """
        return next_link not in self.visited_links and not WikipediaFollower.has_special_wiki_keyword(next_link)

    def crawl_recur(self, url):
        """
        Recursively crawl urls until stopping. Prints out each visit.
        Removes links in parentheses.
        Skips duplicates.
        :param url: the wikipedia url to visit
        :return: None
        """
        print 'visiting link:', url
        self.visited_links[url] = 1  # mark visited
        if self.crawl_over(url):
            print 'finished!'
            return
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        # get body content div
        soup = soup.find("div", id="mw-content-text")
        # soup = soup.find("div", id="bodyContent")
        # remove italics
        [s.extract() for s in soup.find_all("i")]
        # try paragraph tags, then list items, to simulate human user
        next_url = ""
        for tag_type in ["p", "li"]:
            next_url = self.get_candidate_next_url(soup, tag_type)
            if next_url != "":
                self.crawl_recur(next_url)
                break
        if next_url == "":
            print 'at dead end. current url:', url

    def get_candidate_next_url(self, soup, tag_name):
        """
        Finds a candidate for the next url to crawl.
        :param soup: the parsed HTML page
        :param tag_name: the name of the tag type to search
        :return: the url, or an empty string if none found
        """
        next_link = ""
        for p in soup.find_all(tag_name):
            # parse each p, removing parentheses
            smaller_soup = BeautifulSoup(WikipediaFollower.remove_parens(repr(p)), "lxml")
            # select all links with titles
            links = [l for l in smaller_soup.find_all("a") if 'title' in l.attrs]
            if len(links) > 0:  # if we have found links
                next_link = links[0]['href']
                # track possibly changing prefix, only change if we follow the link
                old_prefix = self.wiki_prefix
                if not next_link.startswith(self.wiki_prefix):
                    # if we have a local url, assemble
                    next_link = urlparse.urljoin(self.wiki_prefix, next_link)
                else:  # else we have switched wikipedia-wiktionary
                    self.wiki_prefix = next_link.rpartition('/wiki/')[0]
                # and crawl if we should
                if self.should_visit_link(next_link):
                    return next_link
                else:
                    self.wiki_prefix = old_prefix

        return next_link

    @staticmethod
    def remove_parens(text):
        """
        Removes text in parentheses, unless within a link tag
        :param text: the HTML
        :return: the HTML, with removed parentheses stuff
        """
        # go through text, delete characters if within parens
        text = str(text) + ""  # ensure we have a valid string
        output = ""
        # tracks depth of nested parentheses
        in_parens = 0  # will be greater than zero if we're inside ()
        # tracks depth of nested angular brackets
        in_link = 0  # will be greater than zero if we're inside <a>
        for c in text:
            # if not in parens, check for link open/close
            if in_parens <= 0:
                if c == "<":
                    in_link += 1
                elif c == ">":
                    in_link -= 1
            # if not in a link, check for paren open/close
            if in_link <= 0:
                if c == "(":
                    in_parens += 1
                # write output if we're not in parens
                if in_parens <= 0:
                    output += c
                else:  # else we are in parens, so skip
                    output += ''
                if c == ")":
                    in_parens -= 1
            else:  # else we are in a link, write regardless
                output += c
        return output


def print_help_quit(name):
    """
    Prints help how to use the program
    :param name: the name of the program
    :return:
    """
    print name, '[-s|--startlink] <start_link>'
    print "(If a start link is unspecified, the program starts at a random page.)"
    sys.exit(2)


if __name__ == "__main__":
    try:
        options, args = getopt.getopt(sys.argv[1:], "hs:", ["help", "startlink="])
        start_link = None
        for opt, arg in options:
            if opt in ("-h", "--help"):
                print_help_quit(sys.argv[0])
            elif opt in ("-s", "--startlink"):
                start_link = arg
        wf = WikipediaFollower(start_link)
        wf.crawl()
    except getopt.GetoptError:
        print_help_quit(sys.argv[0])