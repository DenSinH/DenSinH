from generic import *

import json
import jinja2
import re

def html_tag(string):
    return re.sub("[^(a-z)(A-Z)(0-9)._-]", "", string)

loader = jinja2.FileSystemLoader(searchpath="./")
env = jinja2.Environment(loader=loader)
env.filters["html_tag"] = html_tag
template = env.get_template("template.html")

with open("achievements.json", "r") as f:
    achievements = json.load(f)

with open("index.html", "w+") as f:
    f.write(template.render(achievements=achievements))