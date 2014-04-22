#! /usr/bin/env python3

#    spockdoc - A utility for polished documentation
#    Copyright (C) 2014 Troels Brødsgaard
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

# TODO: Test with several input files
# TODO: Unit tests in general

# TODO: Make pdflatex call configurable like pandoc using config file
# and take a path to pdflatex (or xelatex) binary on commandline

# TODO: Test on Windows, might need to use subprocess instead of sh

__author__ = 'troels'

# Standard library imports
from os import path, chdir
from subprocess import call
from configparser import ConfigParser
from tempfile import TemporaryDirectory
import re
from shutil import copy2

# PyPI imports
from docopt import docopt
from sh import git


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
    call(['pdflatex', '-shell-escape', postprocessed_tex_file])
    call(['pdflatex', '-shell-escape', postprocessed_tex_file])

    # TODO: Fix, should not be work_dir but repo dir
    # Above is an assumption, who says we want "compiled" documentation in repo?
    # But fact is, using work_dir is a no go - especially with tmp_dir
    # Fails if it needs folder which isn't there
    # Maybe only overwrite if output_file is not already an abspath?
    output_file = path.join(work_dir, output_file)

    pdf_file = postprocessed_tex_file[:-3] + 'pdf'

    copy2(pdf_file, output_file)

    print('PDF file copied to', output_file)


def process_with_pandoc(pandoc, config, work_dir, preprocessed_markdown_files):
    pandoc_call = [pandoc]

    pandoc_arguments = config['base']['pandoc arguments'].split(' | ')
    pandoc_call += pandoc_arguments

    try:
        pandoc_template = config['base']['template']
        pandoc_call += ['--template=' + pandoc_template]
    except KeyError:
        pass

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

    return pandoc_tex_file


def inject_repository(rules):
    return rules

if __name__ == '__main__':
    arguments = docopt(__doc__)

    # TODO: Test relative paths in config file. Relative to cwd or doc_dir?
    # Template file should be relative to doc_dir or repo
    # or maybe use the magic <repository>?
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
        # TODO: Check key and value for magic injection
        key = re.sub(r'<repository>', repository, key)
        value = re.sub(r'<repository>', repository, value)
        preprocessing_rules.append((key, value))

    preprocessing_rules = inject_repository(preprocessing_rules)

    preprocessed_markdown_files = preprocess(
        markdown_files, preprocessing_rules, doc_dir, work_dir)

    pandoc_tex_file = process_with_pandoc(
        pandoc, config, work_dir, preprocessed_markdown_files)

    postprocessing_rules = list()
    for key, value in config['postprocessing'].items():
        # TODO: Remove duplication
        key = re.sub(r'<repository>', repository, key)
        value = re.sub(r'<repository>', repository, value)
        print(key, value)
        postprocessing_rules.append((key, value))

    postprocessing_rules = inject_repository(postprocessing_rules)

    postprocessed_tex_file = postprocess(pandoc_tex_file, postprocessing_rules,
                                         work_dir)
    output_file = config['base']['output file']
    chdir(work_dir)
    generate_pdf(postprocessed_tex_file, output_file)

    if cleanup_needed:
        tmp_dir.cleanup()

    chdir(repository)
    restore_repository(HEAD)
