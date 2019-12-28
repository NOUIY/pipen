from os import path
from pyppl import PyPPL, Proc, Channel

def fn(fpath):
  return path.basename(fpath).split('.')[0]

pSort          = Proc(desc = 'Sort files.')
pSort.input    = {"infile:file": Channel.fromPattern("./data/*.txt")}
# Notice the different between builtin template engine and Jinja2
pSort.output   = "outfile:file:{{ fn(i.infile) }}.sorted"
# pSort.output   = "outfile:file:{{i.infile | fn}}.sorted"
pSort.forks    = 5
# You have to have Jinja2 installed (pip install Jinja2)
pSort.template = 'Jinja2'
pSort.envs.fn  = fn
pSort.script   = """
  sort -k1r {{i.infile}} > {{o.outfile}}
"""

PyPPL().start(pSort).run()
