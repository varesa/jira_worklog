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
                d[key] = {}

            for worklog in resp.json()['worklogs']:
                author = worklog['author']['name']
                if author not in d[key].keys():
                    d[key][author] = []
                d[key][author].append(worklog['timeSpent'])
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


def print_table(values):
    authors = set()
    for issue in values.keys():
        authors = authors.union(set(values[issue].keys()))


    # Make ordered
    authors = tuple(authors)
    totals = {}

    # Construct the header first as the length will be required later

    header = "| {0:>8}".format("|")
    header_length = 8
    for author in authors:
        header += "{0:>{1}} |".format(author, max(9, len(author)+1))
        header_length += max(11, len(author)+3)
        totals[author] = []

    # Print the header together with some horizontal lines

    print("|{}|".format("-" * header_length))
    print(header)
    print("|{}|".format("-" * header_length))

    # Print the issue details

    for issue in values.keys():
        print("| {0:<6} |".format(issue), end="")
        for author in authors:
            print("{0:>{1}} |".format(sum(values[issue][author]) if author in values[issue].keys() else "",
                                      max(9, len(author)+1)), end="")
            if author in values[issue].keys():
                totals[author].append(sum(values[issue][author]))

        print("")

    # And print the footer with totals (+ some more horizontal lines)

    print("|{}|".format("-" * header_length))
    print("|        |", end="")
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

