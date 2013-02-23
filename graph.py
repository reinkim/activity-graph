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


import colorsys
import datetime
import os
import subprocess
import time

import gflags


FLAGS = gflags.FLAGS


def read_commits(repo_path, branches, since, stats=None):
    stats = stats or {}
    local_offset = datetime.timedelta(seconds=time.timezone)
    log_cmd = ['git', 'log', '--pretty=format:%ci']
    if FLAGS.author:
        log_cmd += ['--author=' + FLAGS.author]
    log_cmd += list(branches)
    result = subprocess.check_output(log_cmd, cwd=repo_path, shell=False)
    for line in result.split('\n'):
        d, t, tz = line.split(' ')
        d = datetime.datetime.strptime(d, '%Y-%m-%d')
        t = datetime.datetime.strptime(t, '%H:%M:%S').time()
        delta = datetime.timedelta(hours=int(tz)/100, minutes=int(tz)%100)
        date = (datetime.datetime.combine(d, t) + delta + local_offset).date()
        if date in stats:
            stats[date] += 1
        else:
            stats[date] = 1
    return stats


def print_graph(output, stats, minDay, maxDay):
    firstDay = minDay - datetime.timedelta(days=minDay.weekday())
    skip = (7 - maxDay.weekday())
    lastDay = maxDay + datetime.timedelta(days=skip)
    weekly = [0] * ((lastDay - firstDay).days / 7)  # per week
    wdayly = [0] * 7  # per wday

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
    main_width = margin * 2 + 12 * int((lastDay - firstDay).days / 7) - 2 + 10
    width = main_width + 40
    main_height = 12 * 7 - 2 + margin * 2 + 10
    height = main_height
    if FLAGS.weekly:
        height += 50 + 10

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
            weekly[column] += data
            wdayly[i] += data
        column += 1
        print >> output, '  </g>'
    print >> output, '</g>'

    if FLAGS.weekly:
        maxima = max(weekly)
        c1 = colorsys.rgb_to_hls(0.1176, 0.4078, 0.1372)
        c2 = colorsys.rgb_to_hls(0.8392, 0.9019, 0.5215)

        def _get_bar_color(_maxima):
            maxima = _maxima
            def _do_get_bar_color(v):
                if v == 0:
                    return '#ffffff'
                p = v / float(maxima)
                q = 1.0 - p
                c = (c1[0] * p + c2[0] * q, c1[1] * p + c2[1] * q,
                     c1[2] * p + c2[2] * q)
                c = colorsys.hls_to_rgb(*c)
                c = tuple(int(_c * 255) for _c in c)
                return '#%02x%02x%02x' % c
            return _do_get_bar_color

        bar = ('  <rect width="8" height="{height}" x="{x}" y="{y}" '
               'style="fill: {fill}"/>')
        print >> output, '<g transform="translate({0}, {1})">'.format(
                          margin + 10, height - 10 - 50)
        get_color = _get_bar_color(maxima)
        for week in xrange(len(weekly)):
            if weekly[week] == 0:
                continue
            bar_height = 50.0 * weekly[week] / maxima
            print >> output, bar.format(x=week * 12 + 2,
                                        y=50 - bar_height,
                                        height=bar_height,
                                        fill=get_color(weekly[week]))
        hr = ('  <line x1="0" y1="{y}" x2="{x}" y2="{y}" '
              'style="stroke-width: 0.9; stroke: #eee; stroke-opacity: 1;"/>')
        print >> output, hr.format(x=main_width - margin * 2 - 10, y=50)
        print >> output, '</g>'

    print >> output, '<g transform="translate({0}, {1})">'.format(
                      main_width, margin + 10)
    bar = ('  <rect height="8" width="{height}" x="0" y="{y}" '
           'style="fill: {fill}"/>')
    vr = ('  <line x1="0" y1="0" x2="0" y2="{height}" '
          'style="stroke-width: 0.9; stroke: #eee; stroke-opacity: 1;"/>')
    maxima = max(wdayly)
    get_color = _get_bar_color(maxima)
    for wday in xrange(7):
        bar_height = 40.0 * wdayly[wday] / maxima
        print >> output, bar.format(height=bar_height, y = wday * 12 + 2,
                                    fill=get_color(wdayly[wday]))
    print >> output, vr.format(height=main_height - 30)
    print >> output, '</g>'

    print >> output, '</svg>'


gflags.DEFINE_string('author', None, 'author to visualize (regex)')
gflags.DEFINE_boolean('weekly', True, 'also draw weekly summary')
gflags.DEFINE_string('since', None, 'generate stats from this day')
gflags.DEFINE_string('until', None, 'generate stats to this day')
gflags.DEFINE_string('out', None, 'output file to save graph')
gflags.MarkFlagAsRequired('out')


def main(argv):
    try:
        argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS repositories\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    if FLAGS.since:
        since = datetime.datetime.strptime(FLAGS.since, '%Y-%m-%d').date()
    else:
        since = datetime.date.today() - datetime.timedelta(days=366)

    if FLAGS.until:
        until = datetime.datetime.strptime(FLAGS.until, '%Y-%m-%d').date()
    else:
        until = datetime.date.today()

    repos = {}
    for repo in argv[1:]:
        if '@' not in repo:
            repo_path = os.path.abspath(repo)
            branch = 'master'
        else:
            repo_path, branch = repo.split('@', 1)
            repo_path = os.path.abspath(repo_path)

        if repo_path not in repos:
            repos[repo_path] = set()
        repos[repo_path].add(branch)

    stats = {}
    for repo_path, branches in repos.iteritems():
        stats = read_commits(repo_path, branches, since, stats)

    with open(FLAGS.out, 'w+') as out:
        print_graph(out, stats, since, until)


if __name__ == '__main__':
    import sys
    main(sys.argv)
