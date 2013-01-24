#!/usr/bin/env python
# vim: fileencoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab

import datetime

from git import Repo
from git.objects import Commit
from pytz import FixedOffset


def read_commits(repo_path, rev=None, stats=None):
    stats = stats or {}
    rev = rev or 'master'
    repo = Repo(repo_path)

    for commit in Commit.iter_items(repo, rev):
        tz = FixedOffset(-commit.committer_tz_offset / 60)
        date = datetime.datetime.fromtimestamp(commit.committed_date, tz)
        date = date.date()
        if date in stats:
            stats[date] += 1
        else:
            stats[date] = 1
    return stats


def print_graph(stats, minDay, maxDay):
    firstDay = minDay - datetime.timedelta(days=minDay.weekday())
    skip = (7 - maxDay.weekday())
    lastDay = maxDay + datetime.timedelta(days=skip)

    def _get_data(d):
        return stats.get(d, 0)

    def _get_color(v):
        if v >= 8: return '#1e6823'
        elif v >= 4: return '#44a340'
        elif v >= 2: return '#8cc665'
        elif v >= 1: return '#d6e685'
        else: return '#eee'

    margin = 10
    # cell width = 10, intra-cell = 2, margin for text = 10
    width = 12 * int((lastDay - firstDay).days / 7) - 2 + margin * 2 + 10
    height = 12 * 7 - 2 + margin * 2 + 10

    # svg boilerplate
    print '<?xml version="1.0" standalone="no"?>'
    print '<svg xmlns="http://www.w3.org/2000/svg"',
    print 'width="{}" height="{}">'.format(width, height)
    print '<!-- {} ~ {} -->'.format(minDay, maxDay)
    print '<!-- {} ~ {} -->'.format(firstDay, lastDay)

    # weekday texts
    wday_text = ('<text dx="10" dy="{0}" text-anchor="middle" '
                 'style="font-size: 9px; fill: {1};">{2}</text>')
    print wday_text.format(28, '#ccc', 'M')
    print wday_text.format(52, '#ccc', 'W')
    print wday_text.format(76, '#ccc', 'F')
    print wday_text.format(100, '#f99', 'S')

    # month labels
    month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # print month-label on column which has first monday of the month
    date = firstDay
    column = 0
    while date < lastDay - datetime.timedelta(days=7):
        if date.day <= 7:
            print ('<text dx="{0}" dy="15" '
                   'style="font-size: 9px; fill: #ccc">{1}</text>').format(
                        column * 12 + 20, month[date.month - 1])
        column += 1
        date += datetime.timedelta(days=7)

    # each day/week
    print '<g transform="translate({}, {})">'.format(margin + 10, margin + 10)
    cell = ('   <rect width="10" height="10" y="{0}" style="fill: {1};">'
            '{2}: {3}</rect>')
    empty = '   <rect width="10" height="10" y="{0}" style="fill: {1};"/>'
    date = firstDay
    column = 0
    while date < lastDay:
        print '  <g transform="translate({}, 0)">'.format(column * 12)
        for i in xrange(7):
            data = _get_data(date)
            color = _get_color(data)
            if data > 0:
                print cell.format(i * 12, color, date, data)
            else:
                print empty.format(i * 12, color)
            date += datetime.timedelta(days=1)
        column += 1
        print '  </g>'

    print '</g>'
    print '</svg>'


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print 'Usage:', sys.argv[0], 'repo-path [rev]'
        sys.exit(1)

    if len(sys.argv) > 2:
        rev = sys.argv[2]
    else:
        rev = None
    stats = read_commits(sys.argv[1], rev)

    if rev:
        minDay = min(stats.keys())
        maxDay = max(stats.keys())
    else:
        # if rev is not given,
        # draw stats from 1 year ago (from today)
        maxDay = datetime.date.today()
        minDay = maxDay - datetime.timedelta(days=365)
    print_graph(stats, minDay, maxDay)
