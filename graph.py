#!/usr/bin/env python
# vim: fileencoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#
# Copyright 2013 Jinuk Kim, rein01@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime
import os

from git import Repo
from git.objects import Commit
import gflags
from pytz import FixedOffset


FLAGS = gflags.FLAGS


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


def print_graph(output, stats, minDay, maxDay):
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
    print >> output, '<?xml version="1.0" standalone="no"?>'
    print >> output, '<svg xmlns="http://www.w3.org/2000/svg"',
    print >> output, 'width="{}" height="{}">'.format(width, height)
    print >> output, '<!-- {} ~ {} -->'.format(minDay, maxDay)
    print >> output, '<!-- {} ~ {} -->'.format(firstDay, lastDay)

    # weekday texts
    wday_text = ('<text dx="10" dy="{0}" text-anchor="middle" '
                 'style="font-size: 9px; fill: {1};">{2}</text>')
    print >> output, wday_text.format(28, '#ccc', 'M')
    print >> output, wday_text.format(52, '#ccc', 'W')
    print >> output, wday_text.format(76, '#ccc', 'F')
    print >> output, wday_text.format(100, '#f99', 'S')

    # month labels
    month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # print month-label on column which has first monday of the month
    date_str = ('<text dx="{0}" dy="15" style="font-size: 9px; fill: #ccc">'
                '{1}</text>')
    date = firstDay
    column = 0
    while date < lastDay - datetime.timedelta(days=7):
        if date.day <= 7:
            print >> output, date_str.format(column * 12 + 20,
                                             month[date.month - 1])
        column += 1
        date += datetime.timedelta(days=7)

    # each day/week
    print >> output, '<g transform="translate({0}, {0})">'.format(margin + 10)
    cell = ('   <rect width="10" height="10" y="{0}" style="fill: {1};">'
            '{2}: {3}</rect>')
    empty = '   <rect width="10" height="10" y="{0}" style="fill: {1};"/>'
    date = firstDay
    column = 0
    while date < lastDay:
        print >> output, '  <g transform="translate({}, 0)">'.format(column * 12)
        for i in xrange(7):
            data = _get_data(date)
            color = _get_color(data)
            if data > 0:
                print >> output, cell.format(i * 12, color, date, data)
            else:
                print >> output, empty.format(i * 12, color)
            date += datetime.timedelta(days=1)
        column += 1
        print >> output, '  </g>'

    print >> output, '</g>'
    print >> output, '</svg>'


gflags.DEFINE_string('since', None, 'generate stats from this day')
gflags.DEFINE_string('out', None, 'output file to save graph')
gflags.MarkFlagAsRequired('out')


def main(argv):
    try:
        argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS repositories\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    if FLAGS.since:
        daySince = datetime.datetime.strptime(FLAGS.since, '%Y-%m-%d').date()
    else:
        daySince = datetime.date.today() - datetime.timedelta(days=366)

    stats = {}
    repoSet = set(os.path.abspath(arg) for arg in argv[1:])
    for repo in repoSet:
        print 'reading {}'.format(repo)
        stats = read_commits(repo, stats=stats)

    lastDay = max(stats.keys())
    with open(FLAGS.out, 'w+') as out:
        print_graph(out, stats, daySince, lastDay)


if __name__ == '__main__':
    import sys
    main(sys.argv)
