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
    stats = stats or ([0] * (24 * 7))
    local_offset = datetime.timedelta(seconds=time.timezone)
    # uses `author-date' in iso8601 format
    log_cmd = ['git', 'log', '--pretty=format:%ai'] + list(branches)
    result = subprocess.check_output(log_cmd, cwd=repo_path, shell=False)
    for line in result.split('\n'):
        d, t, tz = line.split(' ')
        d = datetime.datetime.strptime(d, '%Y-%m-%d')
        t = datetime.datetime.strptime(t, '%H:%M:%S').time()
        delta = datetime.timedelta(hours=int(tz)/100, minutes=int(tz)%100)
        dt = datetime.datetime.combine(d, t)
        dt_local = dt + delta + local_offset
        if dt_local.date() < since:
            continue
        # Intentionaly using auhtor's timezone, since I'm interested in
        # author-time (in one's timezone)
        stats[dt.weekday() * 24 + dt.hour] += 1
    return stats


def print_heatmap(output, stats):

    def _get_data(wday, hour):
        return stats[wday * 24 + hour]

    maxima = max(stats)

    c1 = colorsys.rgb_to_hls(0.1176, 0.4078, 0.1372)
    c2 = colorsys.rgb_to_hls(0.8392, 0.9019, 0.5215)

    def _get_color(v):
        if v == 0:
            return '#ffffff'
        p = v / float(maxima)
        q = 1.0 - p
        c = (c1[0] * p + c2[0] * q, c1[1] * p + c2[1] * q,
             c1[2] * p + c2[2] * q)
        c = colorsys.hls_to_rgb(*c)
        c = tuple(int(_c * 255) for _c in c)
        return '#%02x%02x%02x' % c

    total = sum(stats)
    def _get_percent(v):
        percent = int(v / float(total) * 100)
        return str(percent) + ' %'

    # cell width = 20, height = 10, intra-cell = 1, margin = 10
    cw = 30
    ch = 18
    margin = 10
    width = margin * 2 + (cw + 1) * 24 - 1 + 10 + 10
    height = margin * 2 + (ch + 1) * 7 - 1 + 10 + 10 +  60 + 10

    # svg boilerplate
    print >> output, '<?xml version="1.0" standalone="no"?>'
    print >> output, '<svg xmlns="http://www.w3.org/2000/svg"',
    print >> output, 'width="{}" height="{}">'.format(width, height)

    print >> output, '<g transform="translate({0}, {1})">'.format(
                        margin + 10 + 10, margin + 10)

    cell = ('  <rect width="%d" height="%d" x="{x}" y="{y}" '
            'style="fill: {fill};"/>') % (cw + 1, ch + 1)
    cell_text = ('<text x="{x}" y="{y}" '
                 'style="font-size: 10; fill: black; text-anchor: middle;">'
                 '{text}</text>')
    # for each weekday
    for wday in xrange(7):
        y = (ch + 1) * wday
        for hour in xrange(24):
            v = _get_data(wday, hour)
            if v == 0:
                continue
            x = (cw + 1) * hour
            fill = _get_color(v)
            percent = _get_percent(v)
            print >> output, cell.format(x=x, y=y, fill=fill)
            print >> output, cell_text.format(x=x + cw / 2,
                                              y=y + ch / 2 + 4,
                                              text=percent)

    # draw grid
    hr = ('  <line x1="0" y1="{y}" x2="{x}" y2="{y}" '
          'style="stroke-width: 1; stroke: black; stroke-opacity: 1;"/>')
    for wday in xrange(7 + 1):
        print >> output, hr.format(x=(cw + 1) * 24, y=(ch + 1) * wday)

    vr = ('  <line x1="{x}" y1="0" x2="{x}" y2="{y}" '
          'style="stroke-width: 1; stroke: black; stroke-opacity: 1;"/>')
    for hour in xrange(24 + 1):
        print >> output, vr.format(x=(cw + 1) * hour, y=(ch + 1) * 7)

    # draw label
    wday_text = ('  <text x="{x}" y="{y}" '
                 'style="font-size: 10; fill: black;">{text}</text>')
    for i, w in enumerate(('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')):
        print >> output, wday_text.format(x=-26, y=i * (ch + 1) + 13, text=w)

    hour_text = ('<text x="{x}" y="{y}" '
                 'style="font-size: 10; fill: black; text-anchor: middle;">'
                 '{text}</text>')
    for i, h in enumerate(xrange(25)):
        print >> output, hour_text.format(x=i * (cw + 1), y=-7, text=str(h))
    print >> output, '</g>'

    # second block
    hourly = [0] * 24
    for hour in xrange(24):
        for wday in xrange(7):
            hourly[hour] += _get_data(wday, hour)
    maxima = max(hourly)

    print >> output, '<g transform="translate({0}, {1})">'.format(
                        margin + 10 + 10, height - margin - 70)
    bar = ('  <rect width="%d" height="{height}" x="{x}" y="{y}" '
           'style="fill: {fill};"/>') % (cw - 4,)
    bar_text = ('<text x="{x}" y="%d" '
                'style="font-size: 10; fill: black; text-anchor: middle;">'
                '{text}</text>') % (60 + 10 + 9)

    total = sum(hourly)
    for hour in xrange(24):
        d = hourly[hour]
        if d == 0:
            continue
        bar_height = 60.0 / maxima * d
        text = '%d %%' % int(100.0 * d / total)
        print >> output, bar.format(x=hour * (cw + 1) + 2,
                                    y=70 - bar_height,
                                    height=bar_height,
                                    fill=_get_color(d))
        print >> output, bar_text.format(x=hour * (cw + 1) + cw/2 + 1,
                                         text=text)
    print >> output, hr.format(y=70, x=(cw + 1) * 24)
    print >> output, '</g>'
    print >> output, '</svg>'


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

    stats = None
    for repo_path, branches in repos.iteritems():
        stats = read_commits(repo_path, branches, since, stats)

    with open(FLAGS.out, 'w+') as out:
        print_heatmap(out, stats)


if __name__ == '__main__':
    import sys
    main(sys.argv)
