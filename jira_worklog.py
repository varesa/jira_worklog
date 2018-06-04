import argparse
import requests
import re

from requests.auth import HTTPBasicAuth


API_PATH = "/rest/api/2"


def time_to_int(time):
    m = re.match('.*?([0-9]+)h.*', time)
    if m:
        hours = int(m.group(1))
    else:
        hours = 0

    m = re.match('.*?([0-9]+)m.*', time)
    if m:
        minutes = int(m.group(1))
    else:
        minutes = 0

    return hours, minutes


def sum(times):
    hours = 0
    minutes = 0

    for time in times:
        h, m = time_to_int(time)
        hours += h
        minutes += m

    while minutes >= 60:
        minutes -= 60
        hours += 1

    return "{0:>3}h {1:02d}m".format(hours, minutes)


class Jira:
    def __init__(self, args):
        self.server   = args.server
        self.username = args.username
        self.password = args.password

    def get_issues(self, project):
        resp = requests.get(self.server + API_PATH + "/search?jql=project={}".format(project),
                            auth=HTTPBasicAuth(self.username, self.password))

        if resp.status_code != 200:
            raise Exception("Something went wrong: " + resp.text)

        return resp.json()['issues']

    def get_worklogs(self, issues):
        d = {}
        for issue in issues:
            key = issue['key']
            resp = requests.get(self.server + API_PATH + "/issue/{}/worklog".format(key),
                                auth=HTTPBasicAuth(self.username, self.password))

            if resp.status_code != 200:
                raise Exception("Something went wrong: " + resp.text)

            if len(resp.json()['worklogs']):
                d[key] = {
                    'summary': issue['fields']['summary'],
                    'authors': {}
                }

            for worklog in resp.json()['worklogs']:
                author = worklog['author']['name']
                if author not in d[key]['authors'].keys():
                    d[key]['authors'][author] = []
                d[key]['authors'][author].append(worklog['timeSpent'])
        return d


def get_args():
    parser = argparse.ArgumentParser(description="Get worklog out of Jira")

    parser.add_argument('--server',   type=str, default=None, help="Jira URL")
    parser.add_argument('--username', type=str, default=None, help="Username to Jira")
    parser.add_argument('--password', type=str, default=None, help="Password for Jira")
    parser.add_argument('--project',  type=str, default=None, help="Jira project key")

    args = parser.parse_args()

    if not args.server:
        args.server = input("Server: ")

    if not args.username:
        args.username = input("Username: ")

    if not args.password:
        args.password = input("Password: ")

    if not args.project:
        args.project = input("Project: ")

    return args


def print_table(issues):
    authors = set()
    for issue in issues.keys():
        authors = authors.union(set(issues[issue]['authors'].keys()))


    # Make ordered
    authors = tuple(authors)
    totals = {}

    # Find the longest summary

    summary_length = 0
    for key in issues.keys():
        summary_length = max(summary_length, len(issues[key]['summary']))

    WHITESPACE = 1
    TICKET_ID = 6
    first_column_width = WHITESPACE + TICKET_ID + WHITESPACE + summary_length + WHITESPACE

    # Construct the header first as the length will be required later

    header = "|{0:>{1}}".format("|", first_column_width+1)
    for author in authors:
        header += "{0:>{1}} |".format(author, max(9, len(author)+1))
        totals[author] = []
    header_length = len(header) - 2  # Total line length minus borders

    # Print the header together with some horizontal lines

    print("|{}|".format("-" * header_length))
    print(header)
    print("|{}|".format("-" * header_length))

    # Print the issue details

    for key in issues.keys():
        print("| {0:<6} {1:<{2}} |".format(key, issues[key]['summary'], summary_length), end="")
        for author in authors:
            print("{0:>{1}} |".format(sum(issues[key]['authors'][author]) if author in issues[key]['authors'].keys() else "",
                                      max(9, len(author)+1)), end="")
            if author in issues[key]['authors'].keys():
                totals[author].append(sum(issues[key]['authors'][author]))

        print("")

    # And print the footer with totals (+ some more horizontal lines)

    print("|{}|".format("-" * header_length))
    print("|{0:>{1}}".format("|", first_column_width+1), end="")
    for author in authors:
        print("{0:>{1}} |".format(sum(totals[author]) if author in totals.keys() else "",
                                  max(9, len(author) + 1)), end="")
    print("")
    print("|{}|".format("-" * header_length))


if __name__ == "__main__":
    args = get_args()
    jira = Jira(args)
    worklogs = jira.get_worklogs(jira.get_issues(args.project))
    print_table(worklogs)

