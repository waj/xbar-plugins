#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# <xbar.var>string(VAR_ACCESS_TOKEN=""): GitHub access token</xbar.var>
# <xbar.var>string(VAR_FILTERS=""): Optional filters</xbar.var>

from urllib.request import Request, urlopen
import datetime
import json
import os
import sys

CONFIG_PATH = '~/.xbar.cfg'
DARK_MODE = False # os.environ.get('BitBarDarkMode')

base_query = '''
  search(query: "%(search_query)s", type: ISSUE, first: 100) {
    issueCount
    edges {
      node {
        ... on PullRequest {
          repository {
            nameWithOwner
          }
          author {
            login
          }
          createdAt
          number
          url
          title
          labels(first:100) {
            nodes {
              name
            }
          }
          commits(last: 1) {
            nodes {
              commit {
                status {
                  state
                  contexts {
                    context
                    state
                    targetUrl
                  }
                }
              }
            }
          }
          mergeable
          reviewDecision
          reviewRequests(first: 10) {
            totalCount
            nodes {
              requestedReviewer {
                __typename
                ... on User {
                	login
                }
                ... on Team {
                  name
                }
              }
            }
          }
          isDraft
        }
        ... on Issue {
          repository {
            nameWithOwner
          }
          author {
            login
          }
          createdAt
          number
          url
          title
          labels(first:100) {
            nodes {
              name
            }
          }
        }
      }
    }
  }
'''

colors = {
  'inactive': '#b4b4b4',
  'title': '#ffffff' if DARK_MODE else '#000000',
  'subtitle': '#b4b4b4',
}

state_icons = {
  'EXPECTED': '❓',
  'ERROR': '❌',
  'FAILURE': '❌',
  'PENDING': '⌛',
  'SUCCESS': '✅',
}

pr_icon = 'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9IiMxYTdmMzciIHZpZXdCb3g9IjAgMCAxNiAxNiIgdmVyc2lvbj0iMS4xIiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIGFyaWEtaGlkZGVuPSJ0cnVlIj48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik03LjE3NyAzLjA3M0w5LjU3My42NzdBLjI1LjI1IDAgMDExMCAuODU0djQuNzkyYS4yNS4yNSAwIDAxLS40MjcuMTc3TDcuMTc3IDMuNDI3YS4yNS4yNSAwIDAxMC0uMzU0ek0zLjc1IDIuNWEuNzUuNzUgMCAxMDAgMS41Ljc1Ljc1IDAgMDAwLTEuNXptLTIuMjUuNzVhMi4yNSAyLjI1IDAgMTEzIDIuMTIydjUuMjU2YTIuMjUxIDIuMjUxIDAgMTEtMS41IDBWNS4zNzJBMi4yNSAyLjI1IDAgMDExLjUgMy4yNXpNMTEgMi41aC0xVjRoMWExIDEgMCAwMTEgMXY1LjYyOGEyLjI1MSAyLjI1MSAwIDEwMS41IDBWNUEyLjUgMi41IDAgMDAxMSAyLjV6bTEgMTAuMjVhLjc1Ljc1IDAgMTExLjUgMCAuNzUuNzUgMCAwMS0xLjUgMHpNMy43NSAxMmEuNzUuNzUgMCAxMDAgMS41Ljc1Ljc1IDAgMDAwLTEuNXoiPjwvcGF0aD48L3N2Zz4K'
draft_icon = 'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9IiM1NzYwNmEiIHZpZXdCb3g9IjAgMCAxNiAxNiIgdmVyc2lvbj0iMS4xIiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIGFyaWEtaGlkZGVuPSJ0cnVlIj48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0yLjUgMy4yNWEuNzUuNzUgMCAxMTEuNSAwIC43NS43NSAwIDAxLTEuNSAwek0zLjI1IDFhMi4yNSAyLjI1IDAgMDAtLjc1IDQuMzcydjUuMjU2YTIuMjUxIDIuMjUxIDAgMTAxLjUgMFY1LjM3MkEyLjI1IDIuMjUgMCAwMDMuMjUgMXptMCAxMWEuNzUuNzUgMCAxMDAgMS41Ljc1Ljc1IDAgMDAwLTEuNXptOS41IDNhMi4yNSAyLjI1IDAgMTAwLTQuNSAyLjI1IDIuMjUgMCAwMDAgNC41em0wLTNhLjc1Ljc1IDAgMTAwIDEuNS43NS43NSAwIDAwMC0xLjV6Ij48L3BhdGg+PHBhdGggZD0iTTE0IDcuNWExLjI1IDEuMjUgMCAxMS0yLjUgMCAxLjI1IDEuMjUgMCAwMTIuNSAwem0wLTQuMjVhMS4yNSAxLjI1IDAgMTEtMi41IDAgMS4yNSAxLjI1IDAgMDEyLjUgMHoiPjwvcGF0aD48L3N2Zz4K'
danger_icon = 'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9IiNjZjIyMmUiIHZpZXdCb3g9IjAgMCAxNiAxNiIgdmVyc2lvbj0iMS4xIiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIGFyaWEtaGlkZGVuPSJ0cnVlIj48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0zLjcyIDMuNzJhLjc1Ljc1IDAgMDExLjA2IDBMOCA2Ljk0bDMuMjItMy4yMmEuNzUuNzUgMCAxMTEuMDYgMS4wNkw5LjA2IDhsMy4yMiAzLjIyYS43NS43NSAwIDExLTEuMDYgMS4wNkw4IDkuMDZsLTMuMjIgMy4yMmEuNzUuNzUgMCAwMS0xLjA2LTEuMDZMNi45NCA4IDMuNzIgNC43OGEuNzUuNzUgMCAwMTAtMS4wNnoiPjwvcGF0aD48L3N2Zz4K'
success_icon = 'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9IiMxYTdmMzciIHZpZXdCb3g9IjAgMCAxNiAxNiIgdmVyc2lvbj0iMS4xIiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIGFyaWEtaGlkZGVuPSJ0cnVlIj48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0xMy43OCA0LjIyYS43NS43NSAwIDAxMCAxLjA2bC03LjI1IDcuMjVhLjc1Ljc1IDAgMDEtMS4wNiAwTDIuMjIgOS4yOGEuNzUuNzUgMCAwMTEuMDYtMS4wNkw2IDEwLjk0bDYuNzItNi43MmEuNzUuNzUgMCAwMTEuMDYgMHoiPjwvcGF0aD48L3N2Zz4K'
pending_icon = 'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0iI2JmODcwMCIgdmVyc2lvbj0iMS4xIiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIGFyaWEtaGlkZGVuPSJ0cnVlIj48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik04IDRhNCA0IDAgMTAwIDggNCA0IDAgMDAwLTh6Ij48L3BhdGg+PC9zdmc+Cg=='

def config_error(msg):
  print_line('⚠ Github review requests', color='red')
  print_line('---')
  print_line(msg)
  sys.exit(0)

def execute_query(query):
  headers = {
    'Authorization': 'bearer ' + ACCESS_TOKEN,
    'Content-Type': 'application/json'
  }
  data = json.dumps({'query': query}).encode('utf-8')
  req = Request('https://api.github.com/graphql', data=data, headers=headers)
  body = urlopen(req).read()
  return json.loads(body)

def query(search):
  return base_query % {'search_query': search + ' ' + FILTERS}

def parse_date(text):
  date_obj = datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
  return date_obj.strftime('%B %d, %Y')

def print_line(text, **kwargs):
  text = text.replace("|", "-")
  params = ' '.join(['%s=%s' % (key, value) for key, value in kwargs.items()])
  print('%s | %s' % (text, params) if kwargs.items() else text)

def print_items(response, show_review_status = False):
  for pr in [r['node'] for r in response['edges']]:
    labels = [l['name'] for l in pr['labels']['nodes']]
    title = '#%s: %s' % (pr['number'], pr['title'])
    title_color = colors.get('title')
    subtitle = '%s - opened on %s by @%s' % (
      pr['repository']['nameWithOwner'], parse_date(pr['createdAt']), pr['author']['login'])
    subtitle_color = colors.get('subtitle')
    if pr['mergeable'] == 'CONFLICTING':
      title += ' ⚠️'
    elif 'commits' in pr:
      status = pr['commits']['nodes'][0]['commit']['status']
      if status:
        state = status['state']
        title += ' %s' % state_icons[state]
    if show_review_status:
      review_requested = pr['reviewRequests']['totalCount'] > 0
      review_decision = pr['reviewDecision']
      if review_requested:
        reviewerNames = []
        for requests in pr['reviewRequests']['nodes']:
          reviewer = requests['requestedReviewer']
          if reviewer['__typename'] == 'User':
            reviewerNames.append(reviewer['login'])
          else:
            reviewerNames.append(reviewer['name'])

        subtitle += ', review requested to @%s' % (', @'.join(reviewerNames))
        if review_decision == None or review_decision == 'REVIEW_REQUIRED':
          title += ' ⌛'
        elif review_decision == 'APPROVED':
          title += ' ✅'
        elif review_decision == 'CHANGES_REQUESTED':
          title += ' ❓'
        else:
          title += ' ❌'
      else:
        title += ' 👀'
    icon = draft_icon if pr['isDraft'] else pr_icon

    print_line(title, size=16, color=title_color, href=pr['url'], image=icon)
    print_contexts(pr)
    print_line(subtitle, size=12, color=subtitle_color)

def print_contexts(pr):
  status = pr['commits']['nodes'][0]['commit']['status']
  if status:
    contexts = status['contexts']
    for context in contexts:
      if context['state'] == 'PENDING':
        context_icon = pending_icon
      elif context['state'] == 'SUCCESS':
        context_icon = success_icon
      else:
        context_icon = danger_icon
      print_line("-- %s" % context['context'], href=context['targetUrl'], image=context_icon)

def title(label, href):
  print_line(label, size=16, color='#000000', href=href, font='"Arial Bold"')

if __name__ == '__main__':
  ACCESS_TOKEN = os.environ["VAR_ACCESS_TOKEN"]
  FILTERS = os.environ["VAR_FILTERS"]

  if not all([ACCESS_TOKEN]):
    config_error('ACCESS_TOKEN could not be found')

  bulk_query = '''
  {
    prs: %(prs_query)s
    rev_prs: %(rev_prs_query)s
    issues: %(issues_query)s
    my_prs: %(my_prs_query)s
  }
  ''' % {
    'prs_query': query('type:pr state:open review-requested:@me'),
    'rev_prs_query': query('type:pr state:open reviewed-by:@me review:none'),
    'issues_query': query('type:issue state:open assignee:@me'),
    'my_prs_query': query('type:pr state:open author:@me'),
  }
  response = execute_query(bulk_query)
  data = response['data']

  print_line('#%s' % (data['prs']['issueCount'] + data['rev_prs']['issueCount'] + data['issues']['issueCount']))
  print_line('---')

  title("Awaiting Review", "https://github.com/pulls?q=is%3Aopen+is%3Apr+review-requested%3A%40me" + '+' + FILTERS)
  print_items(data['prs'])
  print_line('---')

  title("Reviewing", "https://github.com/pulls?q=is%3Aopen+is%3Apr+review-requested%3A%40me+reviewed-by%3A%40me" + '+' + FILTERS)
  print_items(data['rev_prs'])
  print_line('---')

  title("My PRs", "https://github.com/pulls?q=is%3Aopen+is%3Apr+author%3A%40me" + '+' + FILTERS)
  print_items(data['my_prs'], show_review_status = True)
  print_line('---')

  title("Issues", "https://github.com/issues/assigned")
  print_items(data['issues'])
