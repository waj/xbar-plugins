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
          number
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
          number
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

pr_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAnFBMVEUAAAAAgEAzZjMrgCskbUkggEAccTkXdC4VgEAUdjsbgDcaezUYgDgbgDYafjgagDcafjYagDYafjgagDcZfjcZgDYbfjgafjYagDgbfzgbgDcbfzcbgDcagDcafzcagDcZfzcbgDYafzcbfzgafzcagDcagDcafzcagDYagDcafzcafzcagDcagDcagDcafzcafzcagDYafzf///+PG9l4AAAAMnRSTlMABAUGBwgJCwwNHB0gTE10dXZ3eHl6e3+Ahayttrq9vr/A0dPV1tjb3N7f7e7y9PX3+D/nbS4AAAABYktHRDM31XxeAAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAAzklEQVQ4je2SxxKCQBBEV0DErASzghmz9v9/nKLjLA5olZ7t275+BcwySn2f2iCDjG6MddOmfgvZm1MkGRepzwgeHulRnxE2gF8KgJj6W45RIyWcAUeVgYtSQ3D6WlgCgdMB5voJSeos+EQ8/Q2VERCyYEf3PiykpqgCB/0OO5mjW3y5BzFM+vi4yQ9CLvkLSazW7diy1DtCKxeZ3AvSod/tsyDIilZuyYIge1q5HQuCPFduwYIgz5VzWRDECO+nicGCJKY7O83aeso88nuu9no3mcA8SOQAAAAASUVORK5CYII='
draft_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAwFBMVEUAAABmZmZVVVVJbW1VVXFNZmZdXXRVampOYmJVXmZaY2tWX2xVYmpYYGlXYWpXYGlYX2tXYGpYYWpXYGtWX2pYYGlXYGpWYWlYYGtXX2pWYGpYYGpXYWtWYGpXYGpWYGpXX2pXYGpWYGtXYWpXYGlYYGpXYGpYYWpXYGpXYGpXYGpXYGtXYWpXYGpXYGpXX2pXYGlXYGpWYGpXYGpXYGtXYGpXYGpXYGpXX2pXYGpXYGpXYGpXYGtXYGpXYGr///+e9zHbAAAAPnRSTlMABQYHCQoLDA0eHzs8PWxtbm9xdXZ3eHl6e3+AgYK5uru8vb6/wMXGx9HS1dbY2tvc5Obn7e7v8vP09fj5/s0fmqMAAAABYktHRD8+YzB1AAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAA+klEQVQ4y62T1xKCQAxFAbH3gl2xKzawN8z/f5ZxyY6LyM44mqfk5rBkw0VR/hGR6vxiGZHQvjaGZwzVMKAOXtREMdW/9JKUL7EXQ2opAn18wqT8CBBXEgB7ETgjcKJ8BVCPNwAWItATTuAzVH0zmOcun0Ebsf5ADd9DGftlTbYqBOS7/ABkS1kpUEQpLwN2KO1kwBaljQwoANxz0iEzpfSP1/wK8Fbts1y047hOW/dZbiR8jOiMSVOPaAQt1yGpxQ3zbjmHJJtVh6DlXJJu3LTvlnNIWrOqRi80XkCbpCar1GHAcvqUSRN+T8O6WhWf5fSW7dpN/S9/9gPOfzauOQIMxAAAAABJRU5ErkJggg=='
danger_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAQlBMVEUAAAD/AAD/AADPIS7PIy7PIi/PIi7PIi7PIi7QIi7QIi7OIi3PIi3QIi7PIi7PIi7PIi7PIi7PIi7PIi7PIi7////iK+crAAAAFHRSTlMAAQJ0hY6PkJaXnJ2e5+rz9Pn8/d/uKJoAAAABYktHRBXl2PmjAAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAAeklEQVQ4y+WTSxKAIAxDSxXR+tfc/6wuZEDRwgFgBZMHDSkQVTXazXFcsT1dAqyABIIF2BPAIRIsAGwCmB7AyMn0Q0xMZIZfPRCq7kuL4Gn35wx1fyR0/faHifO6TpRM+vuFPEiLMhdkLuqu1Kyl1O5mtq8Hc3R1fZgLRDAJzaigTfQAAAAASUVORK5CYII='
success_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAOVBMVEUAAAAAAAAAgAAagDYagDYZgDYZgDgbgDcagDYZfzgagDgafzcagDcafzcagDYafzcagDcafzf////mBwCrAAAAEXRSTlMAAQJadoSOkJaXnJ2e6erx9G46JpsAAAABYktHRBJ7vGwAAAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAAYklEQVQ4y2NgGAV4ARO7ACteeS5BQX4C8oLsuOUZOYDy3EyDSp6Fl40Jxf1caPr5EEJY5RnY4ILY5RHWMnLicB9YBQ8TTnmY0dxYzUcyA6//ISrwhA9YBT55oApmZsbhmvwBvVIGWsVUwUoAAAAASUVORK5CYII='
pending_icon = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAXVBMVEUAAADMmQCqgAC2kgC8hgC+iAC/hQDBiADAiAC+hwC/hwDAhwC/hwC/hgC+hgC/hwC/hwC/iADAhwC/iAC/hwC/hwDAhwDAhwC/hwC/hwC/hwC/hwC+hwC/hwD///+E3WrDAAAAHXRSTlMABQYHKissLY2OkJGTlJaXu7y9vtPU1fHy8/T8/WR5urYAAAABYktHRB5yCiArAAAATmVYSWZNTQAqAAAACAAEARoABQAAAAEAAAA+ARsABQAAAAEAAABGASgAAwAAAAEAAgAAAhMAAwAAAAEAAQAAAAAAAAAAAJAAAAABAAAAkAAAAAElr9YpAAAAdElEQVQYGe3BWxJEMBAF0CvewjzDoN39b3OqfKh0J0twDm6p1s/7Pg8N8srHwZNMDhnll5ePQ+rJyIhEezAiNSxPpYe1UAmwNiorrJXKD9ZCJcAaqHSwGmFEKiQmRjxS7s3Lq0CGG4Un8QXy6j5sW+gq3BJ/m/UWDui1V2kAAAAASUVORK5CYII='

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

def item_numbers(response):
  return [r['node']['number'] for r in response['edges']]

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
    reviewed_prs: %(reviewed_prs_query)s
    rev_prs: %(rev_prs_query)s
    issues: %(issues_query)s
    my_prs: %(my_prs_query)s
  }
  ''' % {
    'prs_query': query('type:pr state:open review-requested:@me'),
    'reviewed_prs_query': query('type:pr state:open reviewed-by:@me review:approved'),
    'rev_prs_query': query('type:pr state:open reviewed-by:@me review:none'),
    'issues_query': query('type:issue state:open assignee:@me'),
    'my_prs_query': query('type:pr state:open author:@me'),
  }
  response = execute_query(bulk_query)
  data = response['data']
  counted_items = item_numbers(data['prs']) + item_numbers(data['rev_prs']) + item_numbers(data['issues'])

  print_line('#%s' % len(set(counted_items)))
  print_line('---')

  title("Awaiting Review", "https://github.com/pulls?q=is%3Aopen+is%3Apr+review-requested%3A%40me" + '+' + FILTERS)
  print_items(data['prs'])
  print_line('---')

  title("Reviewed", "https://github.com/pulls?q=is%3Aopen+is%3Apr+reviewed-by%3A%40me" + '+' + FILTERS)
  print_items(data['reviewed_prs'])
  print_line('---')

  title("Reviewing", "https://github.com/pulls?q=is%3Aopen+is%3Apr+review-requested%3A%40me+reviewed-by%3A%40me" + '+' + FILTERS)
  print_items(data['rev_prs'])
  print_line('---')

  title("My PRs", "https://github.com/pulls?q=is%3Aopen+is%3Apr+author%3A%40me" + '+' + FILTERS)
  print_items(data['my_prs'], show_review_status = True)
  print_line('---')

  title("Issues", "https://github.com/issues/assigned")
  print_items(data['issues'])
