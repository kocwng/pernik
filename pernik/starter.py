"""`python -m pernik init`: a starter pernik.toml, README.md and workflow in the current folder."""
import os

STARTER_TOML = '''# Pernik settings. Edit, then run `python -m pernik preview` or push and let the Action build.
# Every widget kind and its options: `python -m pernik list`
schema = 1
theme = "pernik"
output = "pernik"

[[widget]]
id = "hello"
kind = "hero"
greeting = ["hello", "there!"]
mascot = "banana"

[[widget]]
id = "line"
kind = "divider"
style = "kawung"

[[widget]]
id = "stack-title"
kind = "heading"
text = "tech stack"

[[widget]]
id = "stack"
kind = "stack"
icons = ["python", "javascript", "git"]

[[widget]]
id = "bye"
kind = "footer"
text = "thanks for stopping by!"
'''

STARTER_README = '''<!-- pernik:hello -->
<!-- /pernik:hello -->

Write a few lines about yourself here. Pernik only changes what sits between its markers.

<!-- pernik:line -->
<!-- /pernik:line -->

<!-- pernik:stack-title -->
<!-- /pernik:stack-title -->

<!-- pernik:stack -->
<!-- /pernik:stack -->

<!-- pernik:bye -->
<!-- /pernik:bye -->
'''

WORKFLOW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'examples', 'workflow.yml')


def init(folder):
    made = []
    for name, text in (('pernik.toml', STARTER_TOML), ('README.md', STARTER_README)):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            print(f'{name} already exists, left as is')
            continue
        with open(path, 'w') as f:
            f.write(text)
        made.append(name)
    wf = os.path.join(folder, '.github', 'workflows', 'pernik.yml')
    if os.path.exists(WORKFLOW) and not os.path.exists(wf):
        os.makedirs(os.path.dirname(wf), exist_ok=True)
        with open(WORKFLOW) as src, open(wf, 'w') as dst:
            dst.write(src.read())
        made.append('.github/workflows/pernik.yml')
    print('created: ' + (', '.join(made) or 'nothing'))
    print('next: python -m pernik preview   (then open pernik/preview.html)')
    return 0
