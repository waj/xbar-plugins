#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from urllib.request import Request, urlopen
import configparser
import datetime
import json
import os
import os.path
import subprocess
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

pr_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAAmVBMVEUAAAAAgEAzZjMrgCskbUkggEAccTkXdC4VgEAUdjsbgDcaezUYgDgbgDYafjgagDcafjYagDYafjgagDcZfjcZgDYbfjgafjYagDgbfzgbgDcbfzcbgDcagDcafzcagDcZfzcbgDYafzcbfzgafzcagDcagDcafzcagDYagDcafzcafzcagDcagDcagDcafzcafzcagDYafzceaXBUAAAAMnRSTlMABAUGBwgJCwwNHB0gTE10dXZ3eHl6e3+Ahayttrq9vr/A0dPV1tjb3N7f7e7y9PX3+D/nbS4AAADOSURBVDiN7ZLHEoJAEERXQMSsBLOCGbP2/3+couMsDmiVnu3bvn4FzDJKfZ/aIIOMbox106Z+C9mbUyQZF6nPCB4e6VGfETaAXwqAmPpbjlEjJZwBR5WBi1JDcPpaWAKB0wHm+glJ6iz4RDz9DZURELJgR/c+LKSmqAIH/Q47maNbfLkHMUz6+LjJD0Iu+QtJrNbt2LLUO0IrF5ncC9Kh3+2zIMiKVm7JgiB7WrkdC4I8V27BgiDPlXNZEMQI76eJwYIkpjs7zdp6yjzye672ejeZwDxI5AAAAABJRU5ErkJggg=='
draft_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAwFBMVEUAAABmZmZVVVVJbW1VVXFNZmZdXXRVampOYmJVXmZaY2tWX2xVYmpYYGlXYWpXYGlYX2tXYGpYYWpXYGtWX2pYYGlXYGpWYWlYYGtXX2pWYGpYYGpXYWtWYGpXYGpWYGpXX2pXYGpWYGtXYWpXYGlYYGpXYGpYYWpXYGpXYGpXYGpXYGtXYWpXYGpXYGpXX2pXYGlXYGpWYGpXYGpXYGtXYGpXYGpXYGpXX2pXYGpXYGpXYGpXYGtXYGpXYGr///+e9zHbAAAAPnRSTlMABQYHCQoLDA0eHzs8PWxtbm9xdXZ3eHl6e3+AgYK5uru8vb6/wMXGx9HS1dbY2tvc5Obn7e7v8vP09fj5/s0fmqMAAAABYktHRD8+YzB1AAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAA+klEQVQ4y62T1xKCQAxFAbH3gl2xKzawN8z/f5ZxyY6LyM44mqfk5rBkw0VR/hGR6vxiGZHQvjaGZwzVMKAOXtREMdW/9JKUL7EXQ2opAn18wqT8CBBXEgB7ETgjcKJ8BVCPNwAWItATTuAzVH0zmOcun0Ebsf5ADd9DGftlTbYqBOS7/ABkS1kpUEQpLwN2KO1kwBaljQwoANxz0iEzpfSP1/wK8Fbts1y047hOW/dZbiR8jOiMSVOPaAQt1yGpxQ3zbjmHJJtVh6DlXJJu3LTvlnNIWrOqRi80XkCbpCar1GHAcvqUSRN+T8O6WhWf5fSW7dpN/S9/9gPOfzauOQIMxAAAAABJRU5ErkJggg=='

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
    print_line(subtitle, size=12, color=subtitle_color)

def title(label, href):
  print_line(label, size=16, color='#000000', href=href, font='"Arial Bold"')

if __name__ == '__main__':
  # Read configuration file
  config = configparser.ConfigParser()
  if not any(config.read(os.path.expanduser(CONFIG_PATH))):
    config_error('Could not find configuration file: ' + CONFIG_PATH)
  if not 'github-status' in config:
    config_error('Could not find [github-status] section in config file: ' + CONFIG_PATH)
  config = config['github-status']

  if not 'access_token' in config:
    config_error('Please provide an access_token in the config file: ' + CONFIG_PATH)
  ACCESS_TOKEN = config['access_token']
  if ACCESS_TOKEN == 'from-keychain':
    security_result = subprocess.run(['security', 'find-generic-password', '-s', 'xbar.github-status.token', '-w'], stdout=subprocess.PIPE)
    ACCESS_TOKEN = security_result.stdout.decode('utf-8').rstrip('\n')

  if 'filters' in config:
    FILTERS = config['filters']
  else:
    FILTERS = ''

  if not all([ACCESS_TOKEN]):
    config_error('ACCESS_TOKEN could not be found')
  # END CONFIG

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

  title("PRs", "https://github.com/pulls?q=is%3Aopen+is%3Apr+review-requested%3A%40me" + '+' + FILTERS)
  print_items(data['prs'])
  print_line('---')

  title("Reviewing PRs", "https://github.com/pulls?q=is%3Aopen+is%3Apr+review-requested%3A%40me+reviewed-by%3A%40me" + '+' + FILTERS)
  print_items(data['rev_prs'])
  print_line('---')

  title("My PRs", "https://github.com/pulls?q=is%3Aopen+is%3Apr+author%3A%40me" + '+' + FILTERS)
  print_items(data['my_prs'], show_review_status = True)
  print_line('---')

  title("Issues", "https://github.com/issues/assigned")
  print_items(data['issues'])
