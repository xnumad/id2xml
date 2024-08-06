#!/bin/env python
# -*- coding: utf-8 -*-
# Copyright The IETF Trust 2017, All Rights Reserved

"""
NAME
  id2xml - Convert text format RFCs and Internet-Drafts to .xml format

...

DESCRIPTION
  id2xml reads text-format RFCs and IETF drafts which are reasonably well
  formatted (i.e., conforms to the text format produced by xml2rfc, without
  artwork that extends into the left-hand margin) and tries to generate a
  reasonably appropriate .xml file following the format accepted by xml2rfc,
  defined in RFC 7749 and its predecessors/successors.

  When using id2xml on manually formatted drafts there are sometimes
  issues which cannot be readily judged by software. In such cases,
  manual adjustment of the input text may be the best approach to
  getting acceptable XML output.

  In particular, malformed references may be hard to decipher, despite
  many different patterns being attempted when trying to parse the
  reference. As an example that would require manual fixup of the input,
  here's a reference which this program won't handle (there are no
  quotes around the title, series info occurs before the title, parts
  are separated by colon or periods, rather than commas):

    [AES] National Institute of Standards and Technology. FIPS Pub
          197: Advanced Encryption Standard (AES). 26 November 2001.  
  

OPTIONS
...

AUTHOR
  Written by Henrik Levkowetz, <henrik@levkowetz.com>

COPYRIGHT
  Copyright (c) 2017, The IETF Trust.
  All rights reserved.

  Licenced under the 3-clause BSD license; see the file LICENSE
  for details.
"""


from __future__ import print_function, unicode_literals, division

from __init__ import __version__
from parser import DraftParser
from utils import Options, wrap, strip_pagebreaks, stream_names

try:
    import debug
    debug.debug = True
except ImportError:
    pass

try:
    from pprint import pformat
except ImportError:
    pformat = lambda x: x

_prolog, _middle, _epilog = __doc__.split('...')

# ----------------------------------------------------------------------
#
# This is the entrypoint which is invoked from command-line scripts:

def run():
    import sys, os, argparse
    from pathlib2 import Path
    global _prolog, _middle, _epilog

    program = os.path.basename(sys.argv[0])
    #progdir = os.path.dirname(sys.argv[0])

    # ----------------------------------------------------------------------
    # Parse config file
    # default values
    conf = {
        'logindent':        [4],
        'trace_methods':    [],
        'trace_all':        False,
        'trailing_trace_lines':  10,
        'trace_tail':       -1,
#        'rfc_url':          'https://tools.ietf.org/html/rfc{number}#{fragment}',
#        'draft_url':        'https://tools.ietf.org/html/{draft}#{fragment}',
        }
    for p in ['.', os.environ.get('HOME','.'), '/etc/', ]:
        rcpath = Path(p)
        if rcpath.exists():
            rcfn = rcpath / '.id2xmlrc'
            if rcfn.exists():
                execfile(str(rcfn), conf)
                break
    options = Options(**conf)

    # ----------------------------------------------------------------------
    def say(s):
        msg = "%s\n" % (s)
        sys.stderr.write(wrap(msg))

    # ----------------------------------------------------------------------
    def note(s):
        msg = "%s\n" % (s)
        if not options.quiet:
            sys.stderr.write(wrap(msg))

    # ----------------------------------------------------------------------
    def die(s, error=1):
        msg = "\n%s: Error:  %s\n\n" % (program, s)
        sys.stderr.write(wrap(msg))
        sys.exit(error)

    # ----------------------------------------------------------------------
    # Parse options

    # only show trace options if -d is set
    def debughelp(s):
        if '-d' in sys.argv or '--debug' in sys.argv:
            return s
        else:
            return argparse.SUPPRESS

    def commalist(value):
        return [ s.strip() for s in value.split(',') ]

    class HelpFormatter(argparse.RawDescriptionHelpFormatter):
        def _format_usage(self, usage, actions, groups, prefix):
            global _prolog
            if prefix is None or prefix == 'usage: ':
                prefix = 'SYNOPSIS\n  '
            return _prolog+super(HelpFormatter, self)._format_usage(usage, actions, groups, prefix)

    parser = argparse.ArgumentParser(description=_middle, epilog=_epilog,
                                     formatter_class=HelpFormatter, add_help=False)

    group = parser.add_argument_group(argparse.SUPPRESS)

    group.add_argument('DRAFT', nargs='*',                              help="text format draft(s) to be converted to xml")
    group.add_argument('-2', '--v2', dest='schema', action='store_const', const='v2',
                                                                        help="output v2 (RFC 7749) schema")
    group.add_argument('-3', '--v3', dest='schema', action='store_const', const='v3',
                                                                        help="output v3 (RFC 7991) schema")
    group.add_argument('-d', '--debug', action='store_true',            help="turn on debugging")
    group.add_argument(      '--doc-consensus', metavar='CONS',         help="set the doc consensus, one of yes, no")
    group.add_argument(      '--doc-ipr', metavar='IPR',                help="set the doc ipr value (e.g., trust200902)")
    group.add_argument(      '--doc-stream', metavar='STREAM',          help="set the doc stream, one of IETF, IAB, IRTF, or independent")
    group.add_argument('-h', '--help', action='help',                   help="show this help message and exit")
    group.add_argument('-o', '--out', dest='output_file', metavar='FILE',
                                                                        help="set the output file name")
    group.add_argument('-p', '--path', dest='output_path', metavar="DIR",
                                                                        help="set the output directory name")
    group.add_argument('-q', '--quiet', action='store_true',            help="be more quiet")
    group.add_argument('-s', '--strip-only', action='store_true',       help="don't convert, only strip headers and footers")
    group.add_argument('--trace-start-regex', metavar='REGEX', default=None,
                                                                        help=debughelp("start debug tracing on matching line; requires -d"))
    group.add_argument('--trace-stop-regex',  metavar='REGEX', default='',
                                                                        help=debughelp("stop debug tracing on matching line; requires -d"))
    group.add_argument('--trace-start-line', type=int, metavar='NUMBER', default=None,
                                                                        help=debughelp("start debug tracing on matching line; requires -d"))
    group.add_argument('--trace-stop-line', type=int, metavar='NUMBER', default=None,
                                                                        help=debughelp("stop debug tracing on matching line; requires -d"))
    group.add_argument('--trace-methods', type=commalist, metavar='METHODS',
                                                                        help=debughelp("a comma-separated list of methods to trace; requires -d"))
    group.add_argument('-V', '--version', action='store_true',          help="output version information, then exit")
    group.add_argument('-v', '--verbose', action='store_true',          help="be (slightly) more verbose")
    group.set_defaults(schema='v2')

    options = parser.parse_args(namespace=options)

    # ----------------------------------------------------------------------
    # The program itself    

    if hasattr(globals(), 'debug'):
        debug.debug = options.debug

    if options.version:
        print(program, __version__)
        sys.exit(0)

    if options.output_path and options.output_file:
        die("Mutually exclusive options -o / -p; use one or the other")

    if options.strip_only:
        output_suffix = '.raw'
    else:
        output_suffix = '.xml'

    if options.doc_stream:
        if not options.doc_stream in stream_names:
            die("Expected one of %s for stream, but got '%s'" % (', '.join(stream_names), options.doc_stream))

    if ( ( options.trace_start_regex or options.trace_start_line )
        and not (options.trace_stop_regex or options.trace_stop_line )):
        die("If you set a trace start condition, you must also set a trace stop condition")

    for file in options.DRAFT:
        try:
            inf = Path(file)
            #name = re.sub('-[0-9][0-9]', '', inf.stem)
            if options.output_file:
                # This is not what we want if options.output_file=='-', but we fix
                # that in the 'with' clause below
                outf = Path(options.output_file)
            elif options.output_path:
                outf = Path(options.output_path) / (inf.stem+output_suffix)
            else:
                outf = inf.with_suffix(output_suffix)
                # if we're using an implicit output file name (derived from the
                # input file name), and we're not just stripping headers, refuse
                # to overwrite an existing file.  It could be the original xml
                # file provided by the authors.
                if not options.strip_only and outf.exists():
                    die("The implied output file (%s) already exists.  Provide an explicit "
                        "output filename (with -o) or a directory path (with -p) if you want "
                        "%s to overwrite an existing file." % (outf, program, ))
            with inf.open() as file:
                txt = file.read()
            if options.strip_only:
                note(" Stripping '%s'" % (inf.name, ))
                lines, __ = strip_pagebreaks(txt)
                with (sys.stdout if options.output_file=='-' else outf.open('w')) as out:
                    out.write('\n'.join([l.txt for l in lines]))
                    out.write('\n')
                note(" Written to '%s'" % out.name)
            else:
                note(" Converting '%s'" % (inf.name, ))
                parser = DraftParser(inf.name, txt, options=options)
                xml = parser.parse_to_xml()
                with (sys.stdout if options.output_file=='-' else outf.open('w')) as out:
                    out.write(xml)
                note(" Written to '%s'" % out.name)
        except Exception as e:
            sys.stderr.write("Failure converting %s: %s\n" % (inf.name, e))
            raise


if __name__ == '__main__':
    run()
    
