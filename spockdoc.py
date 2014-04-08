#! /usr/bin/env python3

"""
spockdoc

Usage:
    spockdoc.py [options] <repository>
    spockdoc.py -h | --help

Options:
    -b, --branch=<branch>    Name of repository branch to build
                             documentation for [default: master]
    --commit=<commit>        First six characters of targeted commit, if
                             different from HEAD
                             [default: HEAD]
    -c, --config=<path>      Path to configuration file, relative to repository
                             root [default: doc/spockdoc.conf]
    -d, --docdir=<path>      Path to directory containing documentation files
                             written in markdown relative to repository
                             [default: doc/]
    -p, --pandoc=<path>      Absolute path to pandoc executable
                             [default: pandoc]
    -w, --workdir=<path>     Directory to use for saving temporary files. Use
                             this if you want to keep the non-pdf files
                             generated by pandoc and pdflatex.
    -v, --version            Print version
    -h, --help               Show this screen
"""

# Input format should be as close as possible to standard markdown!
# Necessary conversion pre-pandoc done by preprocessor!

# spockdoc.conf should take arguments like author = author_name and iterate over
# all of them (and just add them, no special case stuff, plain pandoc arguments)
# It is required that ConfigParser can iterate over all keys in a section
# for key in config['bitbucket.org']: print(key)

# references in figures and tables should look like header refs: (#reference)
# and referenced by [text](#reference) - ? Might not work in StackEdit


__author__ = 'troels'

from docopt import docopt
from os import path, chdir
from sh import git
from subprocess import call
from configparser import ConfigParser
from tempfile import TemporaryDirectory
# import requests
import re
from shutil import copy2


def is_valid_repo(repository_path):
    git_path = path.join(repository_path, '.git')

    if path.exists(git_path):
        return True

    return False


def checkout_branch(branch_name):
    git.checkout(branch_name)


def checkout_commit(commit_name):
    if commit == 'HEAD':
        return

    git.checkout(commit_name)


def restore_repository(head):
    git.checkout(head)
    # also reset any changes - THIS IS DANGEROUS STUFF. Best not change files
    # which are being tracked
    # avoid this by using a temporary directory


def get_current_head(repository):
    with open(path.join(repository, '.git/HEAD'), 'r') as head_file:
        head = head_file.readline()
    if 'ref: ' in head:
        head = head.split('/')[-1].strip()

    return head


def preprocess(markdown_files, rules, doc_dir, work_dir):
    preprocessed_markdown_files = list()
    for file in markdown_files:
        markdown_file = path.join(doc_dir, file)
        preprocessed_markdown_file = path.join(work_dir, file)
        with open(markdown_file, 'r') as reader:
            lines = reader.readlines()
        lines = apply_rules(lines, rules)
        with open(preprocessed_markdown_file, 'w') as writer:
            writer.writelines(lines)
        preprocessed_markdown_files.append(preprocessed_markdown_file)

        return preprocessed_markdown_files


def postprocess(pandoc_tex_file, rules, work_dir):
    postprocessed_tex_file = path.join(work_dir, 'postprocess_output.tex')
    with open(pandoc_tex_file, 'r') as reader:
        lines = reader.readlines()
    lines = apply_rules(lines, rules)
    with open(postprocessed_tex_file, 'w') as writer:
        writer.writelines(lines)

    return postprocessed_tex_file


def apply_rules(lines, rules):
    for index, line in enumerate(lines):
        for rule in rules:
            lines[index] = re.sub(rule[0], rule[1], lines[index])

    return lines


def generate_pdf(postprocessed_tex_file, output_file):
    call(['pdflatex', '-output-directory=' + work_dir, postprocessed_tex_file])
    call(['pdflatex', '-output-directory=' + work_dir, postprocessed_tex_file])

    output_file = path.join(work_dir, output_file)

    pdf_file = postprocessed_tex_file[:-3] + 'pdf'

    copy2(pdf_file, output_file)

    print('PDF file copied to', output_file)


def build_pandoc_call(config_parser, tmp_output_file):
    input_files = config_parser['DEFAULT']['input_files'].split(', ')
    pandoc_options = config_parser['DEFAULT']['pandoc_options'].split(', ')
    template = config_parser['DEFAULT']['template']

    authors = config_parser['TEMPLATE_VARIABLES']['authors'].split(', ')
    date = config_parser['TEMPLATE_VARIABLES']['date']

    print(input_files, tmp_output_file)
    print(pandoc_options)
    print(authors)

    pandoc_call = list()
    pandoc_call.append(arguments['--pandoc'])
    pandoc_call += pandoc_options
    pandoc_call.append('--template=' + template)

    for author in authors:
        pandoc_call.append('-V')
        pandoc_call.append('--author=' + author)

    pandoc_call.append('-V')
    pandoc_call.append('--date=' + date)

    pandoc_call.append('-o')
    pandoc_call.append(tmp_output_file)

    pandoc_call += input_files

    print(pandoc_call)

    return pandoc_call


def create_documentation():
    config_path = arguments['--config']

    config_parser = ConfigParser()
    config_parser.read(config_path)

    input_files = config_parser['DEFAULT']['input_files'].split(', ')
    output_file = config_parser['DEFAULT']['output_file']

    chdir('doc')

    with TemporaryDirectory() as tmp_dir:
        for input_file in input_files:
            preprocess(input_file, tmp_dir)

        # need to know the names of the preprocessed files...

        tmp_output_file = tmp_dir + '/output.tex'
        pandoc_call = build_pandoc_call(config_parser, tmp_output_file)
        call(pandoc_call)

        postprocess(tmp_output_file, output_file)


def process_with_pandoc(pandoc, config, work_dir, preprocessed_markdown_files):
    # build pandoc call on preprocessed files
    pandoc_arguments = config['base']['pandoc arguments'].split(' | ')
    pandoc_template = config['base']['template']

    pandoc_call = [pandoc]
    pandoc_call += pandoc_arguments
    pandoc_call += ['--template=' + pandoc_template]

    template_variables = list()
    for key, value in config['template variables'].items():
        values = value.split(' | ')
        for value in values:
            template_variables.append(key + '=' + value)

    for variable in template_variables:
        pandoc_call += ['-V', variable]

    pandoc_tex_file = path.join(work_dir, 'pandoc_output.tex')
    pandoc_call += ['-o', pandoc_tex_file]

    pandoc_call += preprocessed_markdown_files

    call(pandoc_call)
    print(pandoc_call)

    return pandoc_tex_file

if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

    # build absolute paths with abspath
    repository = path.abspath(arguments['<repository>'])
    branch = arguments['--branch']
    commit = arguments['--commit']
    config_file = path.join(repository, arguments['--config'])
    doc_dir = path.join(repository, arguments['--docdir'])
    pandoc = arguments['--pandoc']
    work_dir = arguments['--workdir']
    if work_dir:
        work_dir = path.abspath(work_dir)
        cleanup_needed = False
    else:
        tmp_dir = TemporaryDirectory()
        work_dir = tmp_dir.name
        cleanup_needed = True

    if not is_valid_repo(repository):
        exit('Invalid repository')
    chdir(repository)

    HEAD = get_current_head(repository)  # get the old HEAD for later restore

    checkout_branch(branch)
    checkout_commit(commit)

    config = ConfigParser()
    config.optionxform = str
    config.read(config_file)

    markdown_files = config['base']['input files'].split(' | ')
    preprocessing_rules = list()
    for key, value in config['preprocessing'].items():
        preprocessing_rules.append((key, value))

    preprocessed_markdown_files = preprocess(
        markdown_files, preprocessing_rules, doc_dir, work_dir)

    pandoc_tex_file = process_with_pandoc(
        pandoc, config, work_dir, preprocessed_markdown_files)

    postprocessing_rules = list()
    for key, value in config['postprocessing'].items():
        print(key, value)
        postprocessing_rules.append((key, value))
    #postprocessing_rules.append((r'\\hyperref\[([\w,-]+)\]\{.+\}',
    #                             r'\\autoref{\g<1>}'))

    postprocessed_tex_file = postprocess(pandoc_tex_file, postprocessing_rules,
                                         work_dir)
    output_file = config['base']['output file']
    generate_pdf(postprocessed_tex_file, output_file)

    if cleanup_needed:
        tmp_dir.cleanup()

    restore_repository(HEAD)
